"""
Test Paper Management API views.
"""

from django.db import transaction
from django.db.models import Sum
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.api.permissions import IsTeacher, IsExamCreator
from testpaper.api.filters import TestPaperFilter
from testpaper.api.serializers import (
    AddQuestionsSerializer,
    TestPaperCreateSerializer,
    TestPaperDetailSerializer,
    TestPaperListSerializer,
    TestPaperUpdateSerializer,
)
from testpaper.models import TestPaperInfo, TestPaperTestQ
from testquestion.api.serializers import QuestionDetailSerializer


@extend_schema_view(
    list=extend_schema(
        tags=['papers'],
        summary='시험지 목록 조회',
        description='필터링, 검색, 정렬을 지원하는 시험지 목록 조회 API.',
        parameters=[
            OpenApiParameter(name='search', description='시험지 이름 검색'),
            OpenApiParameter(name='ordering', description='정렬 기준 (create_time, -create_time, total_score, question_count)'),
        ],
    ),
    create=extend_schema(tags=['papers'], summary='시험지 생성'),
    retrieve=extend_schema(tags=['papers'], summary='시험지 상세 조회'),
    update=extend_schema(tags=['papers'], summary='시험지 전체 수정'),
    partial_update=extend_schema(tags=['papers'], summary='시험지 부분 수정'),
    destroy=extend_schema(tags=['papers'], summary='시험지 삭제'),
)
class TestPaperViewSet(viewsets.ModelViewSet):
    """
    시험지 관리 API ViewSet.

    - 교사만 시험지 생성 가능
    - 작성자만 시험지 수정/삭제 가능
    - 모든 인증된 사용자가 조회 가능 (추후 시험 연결로 제한)
    """

    filterset_class = TestPaperFilter
    search_fields = ['name']
    ordering_fields = ['create_time', 'total_score', 'question_count', 'edit_time']
    ordering = ['-create_time']

    def get_queryset(self):
        """
        사용자 유형에 따라 queryset 필터링.
        - 교사: 모든 시험지 조회 가능 (수정은 본인 것만 가능)
        - 학생: 추후 연결된 시험의 시험지만 (현재는 전체)
        """
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return TestPaperInfo.objects.none()

        base_qs = TestPaperInfo.objects.all().select_related('subject', 'create_user').prefetch_related(
            'testpapertestq_set__test_question'
        )

        return base_qs

    def get_permissions(self):
        """
        Action별 Permission 설정.
        """
        if self.action in ['create']:
            return [IsAuthenticated(), IsTeacher()]
        elif self.action in ['update', 'partial_update', 'destroy', 'add_questions', 'remove_question']:
            return [IsAuthenticated(), IsExamCreator()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """
        Action별 Serializer 설정.
        """
        if self.action == 'list':
            return TestPaperListSerializer
        elif self.action == 'retrieve' or self.action == 'preview':
            return TestPaperDetailSerializer
        elif self.action == 'create':
            return TestPaperCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TestPaperUpdateSerializer
        elif self.action == 'add_questions':
            return AddQuestionsSerializer
        return TestPaperDetailSerializer

    @extend_schema(
        tags=['papers'],
        summary='시험지 미리보기',
        description='시험지의 모든 문제와 옵션을 포함한 상세 정보를 조회합니다.',
        responses={200: TestPaperDetailSerializer},
    )
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        시험지 미리보기 (모든 문제 + 옵션 포함).
        """
        paper = self.get_object()
        serializer = TestPaperDetailSerializer(paper)

        # 문제별 옵션 정보 추가
        data = serializer.data
        questions_with_options = []

        for paper_question in paper.testpapertestq_set.all():
            question_data = QuestionDetailSerializer(paper_question.test_question).data
            questions_with_options.append({
                'id': paper_question.id,
                'question': question_data,
                'score': paper_question.score,
                'order': paper_question.order,
            })

        data['questions_with_options'] = questions_with_options
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['papers'],
        summary='시험지에 문제 추가',
        description='시험지에 새로운 문제를 추가합니다. 시험지 작성자만 추가 가능.',
        request=AddQuestionsSerializer,
        responses={200: TestPaperDetailSerializer},
    )
    @action(detail=True, methods=['post'])
    def add_questions(self, request, pk=None):
        """
        시험지에 문제 추가.
        """
        paper = self.get_object()
        serializer = AddQuestionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        questions_data = serializer.validated_data['questions']

        # 중복 문제 검증 (기존 문제 + 새 문제)
        existing_question_ids = set(paper.testpapertestq_set.values_list('test_question_id', flat=True))
        new_question_ids = [q['test_question'].id for q in questions_data]

        duplicates = set(new_question_ids) & existing_question_ids
        if duplicates:
            return Response(
                {'questions': f'이미 시험지에 포함된 문제입니다: {duplicates}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 문제 추가
        with transaction.atomic():
            for question_data in questions_data:
                test_question = question_data['test_question']
                score = question_data.get('score', 5)
                order = question_data.get('order', paper.testpapertestq_set.count() + 1)

                TestPaperTestQ.objects.create(
                    test_paper=paper,
                    test_question=test_question,
                    score=score,
                    order=order,
                )

            # total_score, question_count 재계산
            self._update_paper_stats(paper)

        paper.refresh_from_db()
        return Response(TestPaperDetailSerializer(paper).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['papers'],
        summary='시험지에서 문제 제거',
        description='시험지에서 특정 문제를 제거합니다. 시험지 작성자만 제거 가능.',
        responses={204: None},
    )
    @action(detail=True, methods=['delete'], url_path='remove-question/(?P<question_id>[^/.]+)')
    def remove_question(self, request, pk=None, question_id=None):
        """
        시험지에서 특정 문제 제거.
        """
        paper = self.get_object()

        try:
            paper_question = TestPaperTestQ.objects.get(test_paper=paper, test_question_id=question_id)
        except TestPaperTestQ.DoesNotExist:
            return Response(
                {'detail': '시험지에 해당 문제가 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            paper_question.delete()

            # total_score, question_count 재계산
            self._update_paper_stats(paper)

        paper.refresh_from_db()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _update_paper_stats(self, paper):
        """
        시험지의 total_score와 question_count 재계산.
        """
        # Clear any cached querysets to ensure fresh data
        paper.refresh_from_db()
        result = paper.testpapertestq_set.aggregate(total=Sum('score'))
        paper.total_score = result['total'] or 0
        paper.question_count = paper.testpapertestq_set.count()
        paper.save()
