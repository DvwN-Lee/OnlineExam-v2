"""
User API Tests.
사용자 인증, 프로필, 과목 관리 테스트.
"""
import pytest
from rest_framework.test import APIClient

from user.models import UserProfile, SubjectInfo, StudentsInfo


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teacher_user(db):
    return UserProfile.objects.create_user(
        username='teacher_user', password='testpass123', user_type='teacher', nick_name='Test Teacher'
    )


@pytest.fixture
def student_user(db):
    user = UserProfile.objects.create_user(
        username='student_user', password='testpass123', user_type='student', nick_name='Test Student'
    )
    StudentsInfo.objects.create(
        user=user, student_name='Test Student', student_id='20250001', student_class='1-A', student_school='Test School'
    )
    return user


@pytest.fixture
def subject(db):
    return SubjectInfo.objects.create(subject_name='Test Subject')


@pytest.mark.django_db
class TestUserRegistration:
    """회원가입 테스트"""

    def test_register_teacher_success(self, api_client, subject):
        """교사 회원가입 성공"""
        data = {
            'username': 'newteacher',
            'password': 'newpass123',
            'password2': 'newpass123',
            'nick_name': 'New Teacher',
            'user_type': 'teacher',
            'teacher_name': 'New Teacher',
            'subject_id': subject.id,
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 201
        assert UserProfile.objects.filter(username='newteacher').exists()
        user = UserProfile.objects.get(username='newteacher')
        assert user.user_type == 'teacher'
        assert user.nick_name == 'New Teacher'

    def test_register_student_success(self, api_client):
        """학생 회원가입 성공"""
        data = {
            'username': 'newstudent',
            'password': 'newpass123',
            'password2': 'newpass123',
            'nick_name': 'New Student',
            'user_type': 'student',
            'student_name': 'New Student',
            'student_id': '20250999',
            'student_class': '1-A',
            'student_school': 'Test School',
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 201
        assert UserProfile.objects.filter(username='newstudent').exists()
        user = UserProfile.objects.get(username='newstudent')
        assert user.user_type == 'student'
        assert hasattr(user, 'studentsinfo')
        assert user.studentsinfo.student_name == 'New Student'

    def test_register_duplicate_username_fails(self, api_client, teacher_user):
        """중복 username 회원가입 실패"""
        data = {
            'username': 'teacher_user',  # 이미 존재
            'password': 'newpass123',
            'password2': 'newpass123',
            'nick_name': 'Duplicate',
            'user_type': 'teacher',
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 400

    def test_register_password_mismatch_fails(self, api_client):
        """비밀번호 불일치 회원가입 실패"""
        data = {
            'username': 'newuser',
            'password': 'pass123',
            'password2': 'different123',
            'nick_name': 'New User',
            'user_type': 'student',
            'student_name': 'New Student',
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 400
        assert 'password' in str(response.data)

    def test_register_student_without_name_fails(self, api_client):
        """학생 이름 없이 회원가입 실패"""
        data = {
            'username': 'newstudent',
            'password': 'newpass123',
            'password2': 'newpass123',
            'nick_name': 'New Student',
            'user_type': 'student',
            # student_name 누락
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 400
        assert 'student_name' in str(response.data)

    def test_register_teacher_without_name_fails(self, api_client, subject):
        """교사 이름 없이 회원가입 실패"""
        data = {
            'username': 'newteacher',
            'password': 'newpass123',
            'password2': 'newpass123',
            'nick_name': 'New Teacher',
            'user_type': 'teacher',
            'subject_id': subject.id,
            # teacher_name 누락
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 400
        assert 'teacher_name' in str(response.data)

    def test_register_teacher_without_subject_fails(self, api_client):
        """교사 과목 없이 회원가입 실패"""
        data = {
            'username': 'newteacher',
            'password': 'newpass123',
            'password2': 'newpass123',
            'nick_name': 'New Teacher',
            'user_type': 'teacher',
            'teacher_name': 'New Teacher',
            # subject_id 누락
        }

        response = api_client.post('/api/v1/auth/register/', data, format='json')

        assert response.status_code == 400
        assert 'subject_id' in str(response.data)


@pytest.mark.django_db
class TestAuthentication:
    """인증 테스트"""

    def test_login_success(self, api_client, teacher_user):
        """로그인 성공"""
        data = {'username': 'teacher_user', 'password': 'testpass123'}

        response = api_client.post('/api/v1/auth/token/', data, format='json')

        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password_fails(self, api_client, teacher_user):
        """잘못된 비밀번호 로그인 실패"""
        data = {'username': 'teacher_user', 'password': 'wrongpass'}

        response = api_client.post('/api/v1/auth/token/', data, format='json')

        assert response.status_code == 401

    def test_login_nonexistent_user_fails(self, api_client):
        """존재하지 않는 사용자 로그인 실패"""
        data = {'username': 'nonexistent', 'password': 'somepass'}

        response = api_client.post('/api/v1/auth/token/', data, format='json')

        assert response.status_code == 401

    def test_token_refresh_success(self, api_client, teacher_user):
        """Token 갱신 성공"""
        # 먼저 로그인
        login_data = {'username': 'teacher_user', 'password': 'testpass123'}
        login_response = api_client.post('/api/v1/auth/token/', login_data, format='json')
        refresh_token = login_response.data['refresh']

        # Token 갱신
        refresh_data = {'refresh': refresh_token}
        response = api_client.post('/api/v1/auth/token/refresh/', refresh_data, format='json')

        assert response.status_code == 200
        assert 'access' in response.data


@pytest.mark.django_db
class TestUserProfile:
    """사용자 프로필 테스트"""

    def test_get_profile(self, api_client, teacher_user):
        """프로필 조회"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == 200
        assert response.data['username'] == 'teacher_user'
        assert response.data['user_type'] == 'teacher'

    def test_get_profile_unauthenticated_fails(self, api_client):
        """미인증 사용자 프로필 조회 실패"""
        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == 401

    def test_update_profile(self, api_client, teacher_user):
        """프로필 수정"""
        api_client.force_authenticate(user=teacher_user)
        data = {'nick_name': 'Updated Teacher'}

        response = api_client.patch('/api/v1/users/me/', data, format='json')

        assert response.status_code == 200
        teacher_user.refresh_from_db()
        assert teacher_user.nick_name == 'Updated Teacher'

    def test_update_student_profile_with_info(self, api_client, student_user):
        """학생 추가 정보 포함 프로필 수정"""
        api_client.force_authenticate(user=student_user)
        data = {
            'nick_name': 'Updated Student',
            'student_info': {
                'student_name': 'Updated Name',
                'student_class': '2-B',
            },
        }

        response = api_client.patch('/api/v1/users/me/', data, format='json')

        assert response.status_code == 200
        student_user.refresh_from_db()
        assert student_user.nick_name == 'Updated Student'
        assert student_user.studentsinfo.student_name == 'Updated Name'
        assert student_user.studentsinfo.student_class == '2-B'

    def test_update_teacher_profile_with_info(self, api_client, teacher_user, subject):
        """교사 추가 정보 포함 프로필 수정"""
        # 먼저 TeacherInfo 생성
        from user.models import TeacherInfo
        TeacherInfo.objects.get_or_create(
            user=teacher_user,
            defaults={'teacher_name': 'Original Teacher', 'work_years': 1, 'subject': subject},
        )

        api_client.force_authenticate(user=teacher_user)
        data = {
            'nick_name': 'Updated Teacher',
            'teacher_info': {
                'teacher_name': 'Updated Teacher Name',
                'work_years': 5,
                'subject_id': subject.id,
            },
        }

        response = api_client.patch('/api/v1/users/me/', data, format='json')

        assert response.status_code == 200
        teacher_user.refresh_from_db()
        assert teacher_user.nick_name == 'Updated Teacher'
        assert teacher_user.teacherinfo.teacher_name == 'Updated Teacher Name'
        assert teacher_user.teacherinfo.work_years == 5
        assert teacher_user.teacherinfo.subject == subject


@pytest.mark.django_db
class TestPasswordChange:
    """비밀번호 변경 테스트"""

    def test_change_password_success(self, api_client, teacher_user):
        """비밀번호 변경 성공"""
        api_client.force_authenticate(user=teacher_user)
        data = {'old_password': 'testpass123', 'new_password': 'newpass456', 'new_password2': 'newpass456'}

        response = api_client.put('/api/v1/users/me/change-password/', data, format='json')

        assert response.status_code == 200
        assert '성공적으로 변경되었습니다' in response.data['detail']

        # 새 비밀번호로 로그인 확인
        teacher_user.refresh_from_db()
        assert teacher_user.check_password('newpass456')

    def test_change_password_wrong_old_password_fails(self, api_client, teacher_user):
        """잘못된 기존 비밀번호로 변경 실패"""
        api_client.force_authenticate(user=teacher_user)
        data = {'old_password': 'wrongpass', 'new_password': 'newpass456', 'new_password2': 'newpass456'}

        response = api_client.put('/api/v1/users/me/change-password/', data, format='json')

        assert response.status_code == 400

    def test_change_password_mismatch_fails(self, api_client, teacher_user):
        """새 비밀번호 불일치로 변경 실패"""
        api_client.force_authenticate(user=teacher_user)
        data = {'old_password': 'testpass123', 'new_password': 'newpass456', 'new_password2': 'different456'}

        response = api_client.put('/api/v1/users/me/change-password/', data, format='json')

        assert response.status_code == 400

    def test_change_password_unauthenticated_fails(self, api_client):
        """미인증 사용자 비밀번호 변경 실패"""
        data = {'old_password': 'test', 'new_password': 'new', 'new_password2': 'new'}

        response = api_client.put('/api/v1/users/me/change-password/', data, format='json')

        assert response.status_code == 401


@pytest.mark.django_db
class TestSubjectManagement:
    """과목 관리 테스트"""

    def test_list_subjects(self, api_client, teacher_user, subject):
        """과목 목록 조회"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/subjects/')

        assert response.status_code == 200
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['subject_name'] == 'Test Subject'

    def test_create_subject_as_teacher(self, api_client, teacher_user):
        """교사가 과목 생성"""
        api_client.force_authenticate(user=teacher_user)
        data = {'subject_name': 'New Subject'}

        response = api_client.post('/api/v1/subjects/', data, format='json')

        assert response.status_code == 201
        assert SubjectInfo.objects.filter(subject_name='New Subject').exists()

    def test_create_subject_as_student_forbidden(self, api_client, student_user):
        """학생은 과목 생성 불가"""
        api_client.force_authenticate(user=student_user)
        data = {'subject_name': 'New Subject'}

        response = api_client.post('/api/v1/subjects/', data, format='json')

        assert response.status_code == 403

    def test_update_subject_as_teacher(self, api_client, teacher_user, subject):
        """교사가 과목 수정"""
        api_client.force_authenticate(user=teacher_user)
        data = {'subject_name': 'Updated Subject'}

        response = api_client.patch(f'/api/v1/subjects/{subject.id}/', data, format='json')

        assert response.status_code == 200
        subject.refresh_from_db()
        assert subject.subject_name == 'Updated Subject'

    def test_update_subject_as_student_forbidden(self, api_client, student_user, subject):
        """학생은 과목 수정 불가"""
        api_client.force_authenticate(user=student_user)
        data = {'subject_name': 'Updated'}

        response = api_client.patch(f'/api/v1/subjects/{subject.id}/', data, format='json')

        assert response.status_code == 403

    def test_delete_subject_as_teacher(self, api_client, teacher_user, subject):
        """교사가 과목 삭제"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.delete(f'/api/v1/subjects/{subject.id}/')

        assert response.status_code == 204
        assert not SubjectInfo.objects.filter(id=subject.id).exists()

    def test_delete_subject_as_student_forbidden(self, api_client, student_user, subject):
        """학생은 과목 삭제 불가"""
        api_client.force_authenticate(user=student_user)
        response = api_client.delete(f'/api/v1/subjects/{subject.id}/')

        assert response.status_code == 403
