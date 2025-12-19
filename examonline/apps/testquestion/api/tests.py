"""
Question Management API tests.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from testquestion.models import OptionInfo, TestQuestionInfo
from user.models import SubjectInfo, UserProfile


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teacher_user(db):
    user = UserProfile.objects.create_user(
        username='teacher1', email='teacher@test.com', password='testpass123', user_type='teacher', nick_name='Teacher1'
    )
    return user


@pytest.fixture
def student_user(db):
    user = UserProfile.objects.create_user(
        username='student1', email='student@test.com', password='testpass123', user_type='student', nick_name='Student1'
    )
    return user


@pytest.fixture
def subject(db):
    return SubjectInfo.objects.create(subject_name='Mathematics')


@pytest.fixture
def question_with_options(db, teacher_user, subject):
    question = TestQuestionInfo.objects.create(
        name='Test Question',
        subject=subject,
        score=10,
        tq_type='xz',
        tq_degree='zd',
        is_share=False,
        create_user=teacher_user,
    )
    OptionInfo.objects.create(test_question=question, option='Option A', is_right=True)
    OptionInfo.objects.create(test_question=question, option='Option B', is_right=False)
    OptionInfo.objects.create(test_question=question, option='Option C', is_right=False)
    return question


@pytest.mark.django_db
class TestQuestionCRUD:
    """문제 CRUD 테스트"""

    def test_create_question_as_teacher(self, api_client, teacher_user, subject):
        """교사는 문제를 생성할 수 있다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        data = {
            'name': 'New Question',
            'subject_id': subject.id,
            'score': 5,
            'tq_type': 'xz',
            'tq_degree': 'jd',
            'options': [
                {'option': 'Answer A', 'is_right': True},
                {'option': 'Answer B', 'is_right': False},
            ],
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert TestQuestionInfo.objects.filter(name='New Question').exists()

    def test_create_question_as_student_forbidden(self, api_client, student_user, subject):
        """학생은 문제를 생성할 수 없다"""
        api_client.force_authenticate(user=student_user)
        url = reverse('question-list')
        data = {
            'name': 'New Question',
            'subject_id': subject.id,
            'score': 5,
            'tq_type': 'xz',
            'tq_degree': 'jd',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_questions_as_teacher(self, api_client, teacher_user, question_with_options):
        """교사는 본인 문제와 공유 문제를 조회할 수 있다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) >= 1

    def test_student_cannot_see_unshared_questions(self, api_client, student_user, question_with_options):
        """학생은 공유되지 않은 문제를 볼 수 없다"""
        api_client.force_authenticate(user=student_user)
        url = reverse('question-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # question_with_options is not shared
        assert len(response.data['data']) == 0

    def test_retrieve_question_detail(self, api_client, teacher_user, question_with_options):
        """문제 상세 조회 시 옵션 목록이 포함된다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-detail', kwargs={'pk': question_with_options.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'options' in response.data
        assert len(response.data['options']) == 3

    def test_update_question(self, api_client, teacher_user, question_with_options):
        """문제 생성자는 문제를 수정할 수 있다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-detail', kwargs={'pk': question_with_options.id})
        data = {'name': 'Updated Question Name'}
        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        question_with_options.refresh_from_db()
        assert question_with_options.name == 'Updated Question Name'

    def test_soft_delete_question(self, api_client, teacher_user, question_with_options):
        """문제 삭제 시 Soft Delete가 적용된다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-detail', kwargs={'pk': question_with_options.id})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        question_with_options.refresh_from_db()
        assert question_with_options.is_del is True

    def test_update_question_with_options(self, api_client, teacher_user, question_with_options):
        """문제 수정 시 옵션 내용 및 정답 여부를 변경할 수 있다 (Gemini 권장)"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-detail', kwargs={'pk': question_with_options.id})

        # 기존 옵션 ID 조회
        existing_options = list(question_with_options.optioninfo_set.all())

        data = {
            'name': 'Updated Question',
            'options': [
                {'id': existing_options[0].id, 'option': 'Updated Option A', 'is_right': False},  # 정답 변경
                {'id': existing_options[1].id, 'option': 'Updated Option B', 'is_right': True},   # 새 정답
                {'option': 'New Option D', 'is_right': False},  # 신규 옵션
            ]
        }
        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

        question_with_options.refresh_from_db()
        assert question_with_options.name == 'Updated Question'

        # 옵션 검증
        updated_options = list(question_with_options.optioninfo_set.all())
        assert len(updated_options) == 3  # 기존 2개 + 신규 1개 = 3개 (옵션 C는 삭제됨)

        # 정답 변경 확인
        option_b = next(opt for opt in updated_options if opt.id == existing_options[1].id)
        assert option_b.is_right is True

    def test_deleted_question_not_accessible(self, api_client, teacher_user, question_with_options):
        """삭제된 문제(is_del=True)는 조회 시 404를 반환한다 (Gemini 권장)"""
        # 문제를 삭제 상태로 설정
        question_with_options.is_del = True
        question_with_options.save()

        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-detail', kwargs={'pk': question_with_options.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 목록 조회에서도 나타나지 않음
        list_url = reverse('question-list')
        list_response = api_client.get(list_url)
        assert len(list_response.data['data']) == 0


@pytest.mark.django_db
class TestQuestionFiltering:
    """문제 필터링 테스트"""

    def test_filter_by_subject(self, api_client, teacher_user, question_with_options):
        """과목별 필터링"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        response = api_client.get(url, {'subject': question_with_options.subject.id})
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_type(self, api_client, teacher_user, question_with_options):
        """문제 유형별 필터링"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        response = api_client.get(url, {'tq_type': 'xz'})
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_degree(self, api_client, teacher_user, question_with_options):
        """난이도별 필터링"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        response = api_client.get(url, {'tq_degree': 'zd'})
        assert response.status_code == status.HTTP_200_OK

    def test_search_by_name(self, api_client, teacher_user, question_with_options):
        """문제 제목 검색"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        response = api_client.get(url, {'search': 'Test'})
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestQuestionSharing:
    """문제 공유 기능 테스트"""

    def test_share_question(self, api_client, teacher_user, question_with_options):
        """문제 공유 상태 변경"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-share', kwargs={'pk': question_with_options.id})
        response = api_client.post(url, {'is_share': True}, format='json')
        assert response.status_code == status.HTTP_200_OK
        question_with_options.refresh_from_db()
        assert question_with_options.is_share is True

    def test_student_can_see_shared_question(self, api_client, student_user, question_with_options):
        """공유된 문제는 학생이 조회할 수 있다"""
        # Share the question first
        question_with_options.is_share = True
        question_with_options.save()

        api_client.force_authenticate(user=student_user)
        url = reverse('question-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1


@pytest.mark.django_db
class TestQuestionValidation:
    """문제 유효성 검증 테스트"""

    def test_multiple_choice_requires_options(self, api_client, teacher_user, subject):
        """객관식 문제는 최소 2개 이상의 옵션이 필요하다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        data = {
            'name': 'Invalid Question',
            'subject_id': subject.id,
            'score': 5,
            'tq_type': 'xz',
            'tq_degree': 'jd',
            'options': [
                {'option': 'Only one option', 'is_right': True},
            ],
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_multiple_choice_requires_correct_answer(self, api_client, teacher_user, subject):
        """객관식 문제는 정답 옵션이 필요하다"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-list')
        data = {
            'name': 'No Correct Answer',
            'subject_id': subject.id,
            'score': 5,
            'tq_type': 'xz',
            'tq_degree': 'jd',
            'options': [
                {'option': 'Option A', 'is_right': False},
                {'option': 'Option B', 'is_right': False},
            ],
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMyAndSharedEndpoints:
    """내 문제/공유 문제 Endpoint 테스트"""

    def test_my_questions_endpoint(self, api_client, teacher_user, question_with_options):
        """내 문제 목록 조회"""
        api_client.force_authenticate(user=teacher_user)
        url = reverse('question-my')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_my_questions_forbidden_for_student(self, api_client, student_user):
        """학생은 내 문제 endpoint에 접근할 수 없다"""
        api_client.force_authenticate(user=student_user)
        url = reverse('question-my')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_shared_questions_endpoint(self, api_client, student_user):
        """공유 문제 목록 조회"""
        api_client.force_authenticate(user=student_user)
        url = reverse('question-shared')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
