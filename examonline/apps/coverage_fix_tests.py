"""
Coverage Fix Tests.

특정 validation 및 exception handling 라인을 타겟팅하는 테스트.
일반 테스트에서 도달하기 어려운 edge case를 직접 테스트합니다.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError

from examination.api.taking_views import ExamTakingViewSet
from examination.models import ExaminationInfo, ExamStudentsInfo
from testquestion.api.serializers import QuestionUpdateSerializer
from user.api.serializers import UserRegistrationSerializer
from user.models import UserProfile, SubjectInfo, StudentsInfo


@pytest.mark.django_db
class TestSerializerCoverageFix:
    """
    Serializer validation logic coverage.
    """

    def test_question_update_options_validation_insufficient(self):
        """testquestion/api/serializers.py: options < 2 in update"""
        # PATCH에서 options를 명시적으로 포함하여 validation 트리거
        serializer = QuestionUpdateSerializer(
            data={'tq_type': 'xz', 'options': [{'option': 'Only One'}]}, partial=True
        )
        assert not serializer.is_valid()
        assert 'options' in serializer.errors
        assert '최소 2개' in str(serializer.errors['options'])

    def test_question_update_options_validation_no_correct(self):
        """testquestion/api/serializers.py: no correct answer in update"""
        serializer = QuestionUpdateSerializer(
            data={
                'tq_type': 'xz',
                'options': [
                    {'option': 'A', 'is_right': False},
                    {'option': 'B', 'is_right': False},
                ],
            },
            partial=True,
        )
        assert not serializer.is_valid()
        assert 'options' in serializer.errors
        assert '최소 1개' in str(serializer.errors['options'])

    def test_user_password_mismatch(self):
        """user/api/serializers.py: password mismatch validation"""
        # 모든 required 필드를 포함하여 validate() 도달
        # Django password validator를 통과할 수 있는 강한 password 사용
        serializer = UserRegistrationSerializer(
            data={
                'username': 'testuser_cov',
                'email': 'test@cov.com',
                'password': 'VeryStrongPassword123!@#',
                'password2': 'DifferentPassword456!@#',  # Mismatch
                'nick_name': 'Tester',
                'user_type': 'student',
                'student_name': 'Test Student',
            }
        )
        assert not serializer.is_valid()
        assert 'password' in serializer.errors
        assert '일치하지 않습니다' in str(serializer.errors['password'])


@pytest.mark.django_db
class TestViewExceptionCoverageFix:
    """
    View exception handling coverage.
    """

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.view = ExamTakingViewSet()

    def test_exam_not_found_exceptions(self):
        """examination/api/taking_views.py: DoesNotExist blocks"""
        # User 및 Student 설정
        user = UserProfile.objects.create_user(username='tester_view', password='testpass', user_type='student')
        StudentsInfo.objects.create(user=user, student_name='Tester')

        # Mock request
        request = self.factory.get('/')
        request.user = user
        self.view.request = request
        self.view.format_kwarg = None

        # 존재하지 않는 ID로 각 메서드 호출
        # exam_info
        resp = self.view.exam_info(request, pk=99999)
        assert resp.status_code == 404

        # start
        resp = self.view.start(request, pk=99999)
        assert resp.status_code == 404

        # submit
        resp = self.view.submit(request, pk=99999)
        assert resp.status_code == 404

        # status
        resp = self.view.status(request, pk=99999)
        assert resp.status_code == 404

        # save_draft
        resp = self.view.save_draft(request, pk=99999)
        assert resp.status_code == 404

    def test_exam_start_time_not_yet(self):
        """examination/api/taking_views.py: start time validation"""
        # User 및 Student 설정
        user = UserProfile.objects.create_user(username='tester_time', password='testpass', user_type='student')
        student = StudentsInfo.objects.create(user=user, student_name='Tester')

        # Subject 생성
        subject = SubjectInfo.objects.create(subject_name='Test Subject')

        # 시험 생성자 (교사)
        teacher = UserProfile.objects.create_user(username='teacher_time', password='testpass', user_type='teacher')

        # 미래 시험 생성
        future_time = timezone.now() + timezone.timedelta(days=1)
        exam = ExaminationInfo.objects.create(
            name="Future Exam",
            start_time=future_time,
            end_time=future_time + timezone.timedelta(hours=1),
            subject=subject,
            create_user=teacher,
        )

        # Student를 시험에 등록
        ExamStudentsInfo.objects.create(exam=exam, student=student)

        request = self.factory.post('/')
        request.user = user
        self.view.request = request

        # "아직 시험 시작 시간이 아닙니다" 에러 트리거
        resp = self.view.start(request, pk=exam.id)
        assert resp.status_code == 400
        assert '아직 시험 시작 시간이 아닙니다' in str(resp.data)

    def test_exam_info_no_papers(self):
        """examination/api/taking_views.py: no exam papers error"""
        # User 및 Student 설정
        user = UserProfile.objects.create_user(username='tester_nopaper', password='testpass', user_type='student')
        student = StudentsInfo.objects.create(user=user, student_name='Tester')

        # Subject 생성
        subject = SubjectInfo.objects.create(subject_name='Test Subject')

        # 시험 생성자 (교사)
        teacher = UserProfile.objects.create_user(
            username='teacher_nopaper', password='testpass', user_type='teacher'
        )

        # 시험지 없는 시험 생성
        exam = ExaminationInfo.objects.create(
            name="No Paper Exam",
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            subject=subject,
            create_user=teacher,
        )

        # Student를 시험에 등록 (시험지는 연결 안 함)
        ExamStudentsInfo.objects.create(exam=exam, student=student)

        request = self.factory.get('/')
        request.user = user
        self.view.request = request

        # "시험지가 없습니다" 에러 트리거
        resp = self.view.exam_info(request, pk=exam.id)
        assert resp.status_code == 400
        assert '시험지가 없습니다' in str(resp.data)

    def test_exam_start_no_papers(self):
        """examination/api/taking_views.py: start with no exam papers"""
        # User 및 Student 설정
        user = UserProfile.objects.create_user(username='tester_start_nopaper', password='testpass', user_type='student')
        student = StudentsInfo.objects.create(user=user, student_name='Tester')

        # Subject 생성
        subject = SubjectInfo.objects.create(subject_name='Test Subject')

        # 시험 생성자 (교사)
        teacher = UserProfile.objects.create_user(
            username='teacher_start_nopaper', password='testpass', user_type='teacher'
        )

        # 시험지 없는 시험 생성
        exam = ExaminationInfo.objects.create(
            name="No Paper Start Exam",
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            subject=subject,
            create_user=teacher,
        )

        # Student를 시험에 등록
        ExamStudentsInfo.objects.create(exam=exam, student=student)

        request = self.factory.post('/')
        request.user = user
        self.view.request = request

        # "시험지가 없습니다" 에러 트리거
        resp = self.view.start(request, pk=exam.id)
        assert resp.status_code == 400
        assert '시험지가 없습니다' in str(resp.data)
