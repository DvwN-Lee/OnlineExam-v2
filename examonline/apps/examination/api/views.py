"""
Examination API Views.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from core.api.permissions import IsTeacher, IsExamCreator
from examination.models import ExaminationInfo, ExamPaperInfo, ExamStudentsInfo
from user.models import StudentsInfo

from .filters import ExaminationFilter
from .serializers import (
    ExaminationListSerializer,
    ExaminationDetailSerializer,
    ExaminationCreateSerializer,
    ExaminationUpdateSerializer,
    EnrollStudentsSerializer,
    EnrolledStudentSerializer,
)


class ExaminationViewSet(viewsets.ModelViewSet):
    """
    시험 관리 ViewSet.

    list: 시험 목록 조회
    retrieve: 시험 상세 조회
    create: 시험 생성 (교사 전용)
    update: 시험 수정 (작성자 전용)
    partial_update: 시험 부분 수정 (작성자 전용)
    destroy: 시험 삭제 (작성자 전용)
    enroll_students: 학생 일괄 등록 (작성자 전용)
    enrolled_students: 등록된 학생 목록 조회
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ExaminationFilter
    search_fields = ['name']
    ordering_fields = ['create_time', 'start_time', 'end_time', 'student_num']
    ordering = ['-create_time']

    def get_queryset(self):
        """QuerySet 최적화"""
        user = self.request.user
        base_qs = ExaminationInfo.objects.all().select_related('subject', 'create_user')

        # 학생: 자신이 등록된 시험만
        if user.user_type == 'student':
            try:
                student_info = user.studentsinfo
                return base_qs.filter(examstudentsinfo__student=student_info)
            except Exception:  # pragma: no cover - Defensive: studentsinfo should exist for student user_type
                return base_qs.none()  # pragma: no cover

        # 교사: 모든 시험
        return base_qs

    def get_permissions(self):
        """Action별 권한 설정"""
        if self.action == 'create':
            return [IsAuthenticated(), IsTeacher()]
        elif self.action in ['update', 'partial_update', 'destroy', 'enroll_students']:
            return [IsAuthenticated(), IsExamCreator()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Action별 Serializer 선택"""
        if self.action == 'list':
            return ExaminationListSerializer
        elif self.action == 'retrieve':
            return ExaminationDetailSerializer
        elif self.action == 'create':
            return ExaminationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExaminationUpdateSerializer
        elif self.action == 'enroll_students':
            return EnrollStudentsSerializer
        elif self.action == 'enrolled_students':
            return EnrolledStudentSerializer
        return ExaminationDetailSerializer

    @action(detail=True, methods=['post'])
    def enroll_students(self, request, pk=None):
        """
        학생 일괄 등록.

        Request Body:
        {
            "student_ids": [1, 2, 3, ...]
        }
        """
        exam = self.get_object()

        # 시험 시작 후 등록 불가
        if exam.exam_state != '0':
            return Response(
                {'detail': '시험이 시작되었거나 종료된 경우 학생을 등록할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EnrollStudentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student_ids = serializer.validated_data['student_ids']

        # 이미 등록된 학생 확인
        existing_enrollments = ExamStudentsInfo.objects.filter(
            exam=exam, student_id__in=student_ids
        ).values_list('student_id', flat=True)

        if existing_enrollments:
            return Response(
                {'student_ids': f'이미 등록된 학생이 있습니다: {list(existing_enrollments)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 학생 등록
        with transaction.atomic():
            students = StudentsInfo.objects.filter(id__in=student_ids)
            for student in students:
                ExamStudentsInfo.objects.create(exam=exam, student=student)

            # student_num 업데이트
            exam.student_num = ExamStudentsInfo.objects.filter(exam=exam).count()
            exam.save()

        return Response(
            {'detail': f'{len(student_ids)}명의 학생이 등록되었습니다.', 'student_num': exam.student_num},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def enrolled_students(self, request, pk=None):
        """
        등록된 학생 목록 조회.
        """
        exam = self.get_object()
        enrollments = ExamStudentsInfo.objects.filter(exam=exam).select_related('student')
        serializer = EnrolledStudentSerializer(enrollments, many=True)

        return Response(
            {'exam_id': exam.id, 'exam_name': exam.name, 'students': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def update_state(self, request, pk=None):
        """
        시험 상태 업데이트 (수동).

        Request Body:
        {
            "exam_state": "0" | "1" | "2"
        }
        """
        exam = self.get_object()
        new_state = request.data.get('exam_state')

        if new_state not in ['0', '1', '2']:
            return Response(
                {'exam_state': '올바른 상태가 아닙니다. (0: 시험 전, 1: 시험 중, 2: 시험 종료)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        exam.exam_state = new_state
        exam.save()

        return Response(
            {
                'detail': '시험 상태가 변경되었습니다.',
                'exam_state': exam.exam_state,
                'exam_state_display': exam.get_exam_state_display(),
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """시험 삭제"""
        exam = self.get_object()

        # 시험 시작 후 삭제 불가
        if exam.exam_state != '0':
            return Response(
                {'detail': '시험이 시작되었거나 종료된 경우 삭제할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)
