"""
Question Management API views.
"""

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.api.permissions import IsQuestionOwner, IsTeacher
from testquestion.api.filters import QuestionFilter
from testquestion.api.serializers import (
    QuestionCreateSerializer,
    QuestionDetailSerializer,
    QuestionListSerializer,
    QuestionShareSerializer,
    QuestionUpdateSerializer,
)
from testquestion.models import TestQuestionInfo


@extend_schema_view(
    list=extend_schema(
        tags=['questions'],
        summary='문제 목록 조회',
        description='필터링, 검색, 정렬을 지원하는 문제 목록 조회 API.',
        parameters=[
            OpenApiParameter(name='search', description='문제 제목 검색'),
            OpenApiParameter(name='ordering', description='정렬 기준 (create_time, -create_time, score, -score)'),
        ],
    ),
    create=extend_schema(tags=['questions'], summary='문제 생성'),
    retrieve=extend_schema(tags=['questions'], summary='문제 상세 조회'),
    update=extend_schema(tags=['questions'], summary='문제 전체 수정'),
    partial_update=extend_schema(tags=['questions'], summary='문제 부분 수정'),
    destroy=extend_schema(tags=['questions'], summary='문제 삭제 (Soft Delete)'),
)
class QuestionViewSet(viewsets.ModelViewSet):
    """
    문제 관리 API ViewSet.

    - 교사만 문제 생성/수정/삭제 가능
    - 학생은 공유된 문제만 조회 가능
    - Soft Delete 적용 (is_del=True)
    """

    filterset_class = QuestionFilter
    search_fields = ['name']
    ordering_fields = ['create_time', 'score', 'tq_degree', 'edit_time']
    ordering = ['-create_time']

    def get_queryset(self):
        """
        사용자 유형에 따라 queryset 필터링.
        - 교사: 본인 문제 전체 + 공유 문제
        - 학생: 공유 문제만
        """
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return TestQuestionInfo.objects.none()

        user = self.request.user
        base_qs = TestQuestionInfo.objects.filter(is_del=False)

        if user.user_type == 'teacher':
            # 교사: 본인 문제 + 공유 문제
            return base_qs.filter(Q(create_user=user) | Q(is_share=True)).select_related(
                'subject', 'create_user'
            ).distinct()
        else:
            # 학생: 공유 문제만
            return base_qs.filter(is_share=True).select_related('subject', 'create_user')

    def get_permissions(self):
        """
        Action별 Permission 설정.
        """
        if self.action in ['create']:
            return [IsAuthenticated(), IsTeacher()]
        elif self.action in ['update', 'partial_update', 'destroy', 'share']:
            return [IsAuthenticated(), IsQuestionOwner()]
        return [IsAuthenticated(), IsQuestionOwner()]

    def get_serializer_class(self):
        """
        Action별 Serializer 설정.
        """
        if self.action == 'list':
            return QuestionListSerializer
        elif self.action == 'retrieve':
            return QuestionDetailSerializer
        elif self.action == 'create':
            return QuestionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return QuestionUpdateSerializer
        elif self.action == 'share':
            return QuestionShareSerializer
        elif self.action in ['my', 'shared']:
            return QuestionListSerializer
        return QuestionDetailSerializer

    def perform_destroy(self, instance):
        """
        Soft Delete 구현.
        """
        instance.is_del = True
        instance.save()

    @extend_schema(
        tags=['questions'],
        summary='문제 공유 상태 변경',
        description='문제의 공유 상태를 변경합니다. 문제 생성자만 변경 가능.',
        request=QuestionShareSerializer,
        responses={200: QuestionDetailSerializer},
    )
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """
        문제 공유 상태 토글.
        """
        question = self.get_object()
        serializer = QuestionShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question.is_share = serializer.validated_data['is_share']
        question.save()

        return Response(QuestionDetailSerializer(question).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['questions'],
        summary='내 문제 목록',
        description='현재 로그인한 교사가 생성한 문제 목록을 조회합니다.',
    )
    @action(detail=False, methods=['get'])
    def my(self, request):
        """
        내가 생성한 문제 목록 조회 (교사 전용).
        """
        if request.user.user_type != 'teacher':
            return Response({'detail': '교사만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)

        queryset = (
            TestQuestionInfo.objects.filter(create_user=request.user, is_del=False)
            .select_related('subject', 'create_user')
            .order_by('-create_time')
        )

        # Apply filters
        queryset = self.filter_queryset(queryset)

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['questions'],
        summary='공유 문제 목록',
        description='공유된 문제 목록을 조회합니다. 모든 인증된 사용자가 접근 가능.',
    )
    @action(detail=False, methods=['get'])
    def shared(self, request):
        """
        공유된 문제 목록 조회.
        """
        queryset = (
            TestQuestionInfo.objects.filter(is_share=True, is_del=False)
            .select_related('subject', 'create_user')
            .order_by('-create_time')
        )

        # Apply filters
        queryset = self.filter_queryset(queryset)

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
