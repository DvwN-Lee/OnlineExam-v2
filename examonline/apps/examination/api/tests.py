"""
Examination API Tests.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from examination.models import ExaminationInfo, ExamPaperInfo, ExamStudentsInfo
from testpaper.models import TestPaperInfo
from user.models import UserProfile, SubjectInfo, StudentsInfo


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teacher_user(db):
    return UserProfile.objects.create_user(
        username='teacher_exam', password='testpass123', user_type='teacher', nick_name='Exam Teacher'
    )


@pytest.fixture
def another_teacher(db):
    return UserProfile.objects.create_user(
        username='teacher2', password='testpass123', user_type='teacher', nick_name='Another Teacher'
    )


@pytest.fixture
def student_user(db):
    user = UserProfile.objects.create_user(
        username='student_exam', password='testpass123', user_type='student', nick_name='Exam Student'
    )
    StudentsInfo.objects.create(
        user=user, student_name='Exam Student', student_id='20250001', student_class='1-A', student_school='Test School'
    )
    return user


@pytest.fixture
def subject(db):
    return SubjectInfo.objects.create(subject_name='Exam Subject')


@pytest.fixture
def test_paper(db, teacher_user, subject):
    return TestPaperInfo.objects.create(
        name='Test Paper for Exam',
        subject=subject,
        tp_degree='jd',
        total_score=100,
        question_count=10,
        passing_score=60,
        create_user=teacher_user,
    )


@pytest.fixture
def examination(db, teacher_user, subject):
    start_time = timezone.now() + timedelta(days=1)
    return ExaminationInfo.objects.create(
        name='Test Examination',
        subject=subject,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        exam_state='0',
        exam_type='pt',
        student_num=0,
        actual_num=0,
        create_user=teacher_user,
    )


@pytest.mark.django_db
class TestExaminationCRUD:
    """시험 CRUD 테스트"""

    def test_create_examination_success(self, api_client, teacher_user, subject, test_paper):
        """시험 생성 성공"""
        api_client.force_authenticate(user=teacher_user)
        start_time = (timezone.now() + timedelta(days=1)).isoformat()

        data = {
            'name': 'New Exam',
            'subject_id': subject.id,
            'start_time': start_time,
            'duration': 120,  # 2 hours
            'exam_type': 'pt',
            'papers': [{'paper_id': test_paper.id}],
        }

        response = api_client.post('/api/v1/exams/', data, format='json')

        assert response.status_code == 201
        assert response.data['name'] == 'New Exam'
        assert response.data['student_num'] == 0
        assert response.data['exam_state'] == '0'

        # 시험지 연결 확인
        exam = ExaminationInfo.objects.get(id=response.data['id'])
        assert ExamPaperInfo.objects.filter(exam=exam).count() == 1

    def test_create_examination_without_papers_fails(self, api_client, teacher_user, subject):
        """시험지 없이 시험 생성 실패"""
        api_client.force_authenticate(user=teacher_user)
        start_time = (timezone.now() + timedelta(days=1)).isoformat()

        data = {'name': 'New Exam', 'subject_id': subject.id, 'start_time': start_time, 'duration': 120, 'papers': []}

        response = api_client.post('/api/v1/exams/', data, format='json')

        assert response.status_code == 400
        assert 'papers' in response.data['error']['details']

    def test_create_examination_past_start_time_fails(self, api_client, teacher_user, subject, test_paper):
        """과거 시작 시간으로 시험 생성 실패"""
        api_client.force_authenticate(user=teacher_user)
        start_time = (timezone.now() - timedelta(days=1)).isoformat()

        data = {
            'name': 'New Exam',
            'subject_id': subject.id,
            'start_time': start_time,
            'duration': 120,
            'papers': [{'paper_id': test_paper.id}],
        }

        response = api_client.post('/api/v1/exams/', data, format='json')

        assert response.status_code == 400
        assert 'start_time' in response.data['error']['details']

    def test_list_examinations(self, api_client, teacher_user, examination):
        """시험 목록 조회"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/v1/exams/')

        assert response.status_code == 200
        assert response.data['meta']['count'] == 1
        assert response.data['data'][0]['name'] == 'Test Examination'

    def test_retrieve_examination(self, api_client, teacher_user, examination, test_paper):
        """시험 상세 조회"""
        ExamPaperInfo.objects.create(exam=examination, paper=test_paper)
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/v1/exams/{examination.id}/')

        assert response.status_code == 200
        assert response.data['name'] == 'Test Examination'
        assert len(response.data['papers']) == 1

    def test_update_examination(self, api_client, teacher_user, examination):
        """시험 수정"""
        api_client.force_authenticate(user=teacher_user)

        data = {'name': 'Updated Exam Name', 'duration': 180}

        response = api_client.patch(f'/api/v1/exams/{examination.id}/', data, format='json')

        assert response.status_code == 200
        examination.refresh_from_db()
        assert examination.name == 'Updated Exam Name'

    def test_update_started_examination_fails(self, api_client, teacher_user, examination):
        """시작된 시험 수정 실패"""
        examination.exam_state = '1'  # 시험 중
        examination.save()
        api_client.force_authenticate(user=teacher_user)

        data = {'name': 'Updated Name'}

        response = api_client.patch(f'/api/v1/exams/{examination.id}/', data, format='json')

        assert response.status_code == 400

    def test_delete_examination(self, api_client, teacher_user, examination):
        """시험 삭제"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.delete(f'/api/v1/exams/{examination.id}/')

        assert response.status_code == 204
        assert not ExaminationInfo.objects.filter(id=examination.id).exists()

    def test_delete_started_examination_fails(self, api_client, teacher_user, examination):
        """시작된 시험 삭제 실패"""
        examination.exam_state = '1'
        examination.save()
        api_client.force_authenticate(user=teacher_user)

        response = api_client.delete(f'/api/v1/exams/{examination.id}/')

        assert response.status_code == 400


@pytest.mark.django_db
class TestStudentEnrollment:
    """학생 등록 테스트"""

    def test_enroll_students_success(self, api_client, teacher_user, examination):
        """학생 일괄 등록 성공"""
        # 학생 생성
        student1 = UserProfile.objects.create_user(username='student1', password='pass', user_type='student')
        student2 = UserProfile.objects.create_user(username='student2', password='pass', user_type='student')
        student_info1 = StudentsInfo.objects.create(user=student1, student_name='Student 1', student_id='001')
        student_info2 = StudentsInfo.objects.create(user=student2, student_name='Student 2', student_id='002')

        api_client.force_authenticate(user=teacher_user)

        data = {'student_ids': [student_info1.id, student_info2.id]}

        response = api_client.post(f'/api/v1/exams/{examination.id}/enroll_students/', data, format='json')

        assert response.status_code == 200
        assert response.data['student_num'] == 2
        examination.refresh_from_db()
        assert examination.student_num == 2

    def test_enroll_duplicate_students_fails(self, api_client, teacher_user, examination):
        """중복 학생 등록 실패"""
        student = UserProfile.objects.create_user(username='student1', password='pass', user_type='student')
        student_info = StudentsInfo.objects.create(user=student, student_name='Student 1', student_id='001')
        ExamStudentsInfo.objects.create(exam=examination, student=student_info)

        api_client.force_authenticate(user=teacher_user)

        data = {'student_ids': [student_info.id]}

        response = api_client.post(f'/api/v1/exams/{examination.id}/enroll_students/', data, format='json')

        assert response.status_code == 400
        assert 'student_ids' in response.data

    def test_enroll_students_after_exam_start_fails(self, api_client, teacher_user, examination):
        """시험 시작 후 학생 등록 실패"""
        examination.exam_state = '1'
        examination.save()

        student = UserProfile.objects.create_user(username='student1', password='pass', user_type='student')
        student_info = StudentsInfo.objects.create(user=student, student_name='Student 1', student_id='001')

        api_client.force_authenticate(user=teacher_user)

        data = {'student_ids': [student_info.id]}

        response = api_client.post(f'/api/v1/exams/{examination.id}/enroll_students/', data, format='json')

        assert response.status_code == 400

    def test_get_enrolled_students(self, api_client, teacher_user, examination):
        """등록된 학생 목록 조회"""
        student = UserProfile.objects.create_user(username='student1', password='pass', user_type='student')
        student_info = StudentsInfo.objects.create(user=student, student_name='Student 1', student_id='001')
        ExamStudentsInfo.objects.create(exam=examination, student=student_info)

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/v1/exams/{examination.id}/enrolled_students/')

        assert response.status_code == 200
        assert len(response.data['students']) == 1
        assert response.data['students'][0]['student']['student_name'] == 'Student 1'


@pytest.mark.django_db
class TestPermissions:
    """권한 테스트"""

    def test_student_cannot_create_exam(self, api_client, student_user, subject, test_paper):
        """학생은 시험 생성 불가"""
        api_client.force_authenticate(user=student_user)
        start_time = (timezone.now() + timedelta(days=1)).isoformat()

        data = {
            'name': 'New Exam',
            'subject_id': subject.id,
            'start_time': start_time,
            'duration': 120,
            'papers': [{'paper_id': test_paper.id}],
        }

        response = api_client.post('/api/v1/exams/', data, format='json')

        assert response.status_code == 403

    def test_non_creator_cannot_update_exam(self, api_client, another_teacher, examination):
        """작성자가 아닌 교사는 시험 수정 불가"""
        api_client.force_authenticate(user=another_teacher)

        data = {'name': 'Updated Name'}

        response = api_client.patch(f'/api/v1/exams/{examination.id}/', data, format='json')

        assert response.status_code == 403

    def test_student_can_view_enrolled_exams(self, api_client, student_user, examination):
        """학생은 자신이 등록된 시험만 조회 가능"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=examination, student=student_info)

        api_client.force_authenticate(user=student_user)

        response = api_client.get('/api/v1/exams/')

        assert response.status_code == 200
        assert response.data['meta']['count'] == 1


@pytest.mark.django_db
class TestFiltering:
    """필터링 테스트"""

    def test_filter_by_exam_state(self, api_client, teacher_user, examination):
        """시험 상태로 필터링"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/v1/exams/', {'exam_state': '0'})

        assert response.status_code == 200
        assert response.data['meta']['count'] == 1

    def test_filter_by_subject(self, api_client, teacher_user, subject, examination):
        """과목으로 필터링"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/v1/exams/', {'subject': subject.id})

        assert response.status_code == 200
        assert response.data['meta']['count'] == 1

    def test_search_by_name(self, api_client, teacher_user, examination):
        """이름으로 검색"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/v1/exams/', {'search': 'Test'})

        assert response.status_code == 200
        assert response.data['meta']['count'] == 1
