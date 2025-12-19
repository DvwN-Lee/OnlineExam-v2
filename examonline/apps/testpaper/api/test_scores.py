"""
Scores API Tests.
성적 조회 및 관리 API 테스트.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from examination.models import ExaminationInfo, ExamPaperInfo, ExamStudentsInfo
from testpaper.models import TestPaperInfo, TestPaperTestQ, TestScores
from testquestion.models import TestQuestionInfo, OptionInfo
from user.models import UserProfile, SubjectInfo, StudentsInfo


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teacher_user(db):
    return UserProfile.objects.create_user(
        username='teacher_scores', password='testpass123', user_type='teacher', nick_name='Scores Teacher'
    )


@pytest.fixture
def another_teacher(db):
    return UserProfile.objects.create_user(
        username='teacher2_scores', password='testpass123', user_type='teacher', nick_name='Another Teacher'
    )


@pytest.fixture
def student_user(db):
    user = UserProfile.objects.create_user(
        username='student_scores', password='testpass123', user_type='student', nick_name='Scores Student'
    )
    StudentsInfo.objects.create(
        user=user,
        student_name='Scores Student',
        student_id='20250201',
        student_class='2-A',
        student_school='Test School',
    )
    return user


@pytest.fixture
def student_user2(db):
    user = UserProfile.objects.create_user(
        username='student_scores2', password='testpass123', user_type='student', nick_name='Student 2'
    )
    StudentsInfo.objects.create(
        user=user, student_name='Student 2', student_id='20250202', student_class='2-B', student_school='Test School'
    )
    return user


@pytest.fixture
def subject(db):
    return SubjectInfo.objects.create(subject_name='Scores Subject')


@pytest.fixture
def multiple_choice_question(db, teacher_user, subject):
    """객관식 문제"""
    question = TestQuestionInfo.objects.create(
        name='What is 2+2?',
        subject=subject,
        score=10,
        tq_type='xz',
        tq_degree='jd',
        create_user=teacher_user,
    )
    OptionInfo.objects.create(test_question=question, option='3', is_right=False)
    OptionInfo.objects.create(test_question=question, option='4', is_right=True)
    OptionInfo.objects.create(test_question=question, option='5', is_right=False)
    return question


@pytest.fixture
def true_false_question(db, teacher_user, subject):
    """OX 문제"""
    question = TestQuestionInfo.objects.create(
        name='Python is a programming language', subject=subject, score=5, tq_type='pd', tq_degree='jd', create_user=teacher_user
    )
    OptionInfo.objects.create(test_question=question, option='True', is_right=True)
    OptionInfo.objects.create(test_question=question, option='False', is_right=False)
    return question


@pytest.fixture
def test_paper(db, teacher_user, subject, multiple_choice_question, true_false_question):
    """시험지"""
    paper = TestPaperInfo.objects.create(
        name='Scores Test Paper',
        subject=subject,
        tp_degree='jd',
        total_score=15,
        passing_score=9,
        question_count=2,
        create_user=teacher_user,
    )
    TestPaperTestQ.objects.create(test_paper=paper, test_question=multiple_choice_question, score=10, order=1)
    TestPaperTestQ.objects.create(test_paper=paper, test_question=true_false_question, score=5, order=2)
    return paper


@pytest.fixture
def examination(db, teacher_user, subject, test_paper):
    """시험"""
    start_time = timezone.now() - timedelta(days=1)
    exam = ExaminationInfo.objects.create(
        name='Scores Exam',
        subject=subject,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        exam_state='2',  # 종료
        exam_type='pt',
        student_num=0,
        actual_num=0,
        create_user=teacher_user,
    )
    ExamPaperInfo.objects.create(exam=exam, paper=test_paper)
    return exam


@pytest.fixture
def submitted_score(db, examination, student_user, test_paper, multiple_choice_question, true_false_question):
    """제출된 성적"""
    return TestScores.objects.create(
        exam=examination,
        user=student_user.studentsinfo,
        test_paper=test_paper,
        start_time=timezone.now() - timedelta(hours=2),
        submit_time=timezone.now() - timedelta(hours=1),
        is_submitted=True,
        test_score=15,  # 만점
        time_used=60,
        detail_records={
            str(multiple_choice_question.id): {'answer': '2', 'is_correct': True, 'score': 10, 'max_score': 10},
            str(true_false_question.id): {'answer': '1', 'is_correct': True, 'score': 5, 'max_score': 5},
        },
    )


@pytest.mark.django_db
class TestMyScores:
    """학생 성적 조회 테스트"""

    def test_my_scores_list(self, api_client, student_user, submitted_score):
        """내 성적 목록 조회"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/v1/scores/my/')

        assert response.status_code == 200
        assert len(response.data['scores']) == 1
        assert response.data['scores'][0]['test_score'] == 15
        assert response.data['scores'][0]['passed'] is True

    def test_my_scores_list_teacher_forbidden(self, api_client, teacher_user):
        """교사는 내 성적 조회 불가"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/scores/my/')

        assert response.status_code == 403
        assert '학생 정보를 찾을 수 없습니다' in response.data['detail']

    def test_my_score_detail(self, api_client, student_user, submitted_score, examination):
        """내 성적 상세 조회"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/scores/my/{examination.id}/')

        assert response.status_code == 200
        assert response.data['test_score'] == 15
        assert response.data['passed'] is True
        assert len(response.data['question_results']) == 2
        assert response.data['question_results'][0]['is_correct'] is True

    def test_my_score_detail_not_submitted(self, api_client, student_user, examination):
        """제출하지 않은 시험 조회 실패"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/scores/my/{examination.id}/')

        assert response.status_code == 404
        assert '제출한 성적이 없습니다' in response.data['detail']

    def test_my_score_detail_another_exam(self, api_client, student_user):
        """존재하지 않는 시험 조회 실패"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/v1/scores/my/99999/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestExamScores:
    """교사용 시험별 성적 조회 테스트"""

    def test_exam_scores_list(self, api_client, teacher_user, examination, submitted_score):
        """시험별 성적 목록 조회"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/')

        assert response.status_code == 200
        assert response.data['exam_name'] == 'Scores Exam'
        assert len(response.data['scores']) == 1
        assert response.data['scores'][0]['test_score'] == 15

    def test_exam_scores_student_forbidden(self, api_client, student_user, examination):
        """학생은 시험 성적 조회 불가"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/')

        assert response.status_code == 403
        assert '교사만 접근할 수 있습니다' in response.data['detail']

    def test_exam_scores_not_creator(self, api_client, another_teacher, examination):
        """시험 작성자가 아닌 교사는 조회 불가"""
        api_client.force_authenticate(user=another_teacher)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/')

        assert response.status_code == 403
        assert '권한이 없습니다' in response.data['detail']

    def test_exam_scores_not_found(self, api_client, teacher_user):
        """존재하지 않는 시험 조회 실패"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/scores/exam/99999/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestExamStatistics:
    """시험 성적 통계 테스트"""

    def test_exam_statistics(self, api_client, teacher_user, examination, student_user, student_user2, submitted_score):
        """성적 통계 조회"""
        # 학생들 등록
        ExamStudentsInfo.objects.create(exam=examination, student=student_user.studentsinfo)
        ExamStudentsInfo.objects.create(exam=examination, student=student_user2.studentsinfo)

        # student2 성적 추가 (불합격)
        TestScores.objects.create(
            exam=examination,
            user=student_user2.studentsinfo,
            test_paper=examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(hours=2),
            submit_time=timezone.now() - timedelta(hours=1),
            is_submitted=True,
            test_score=5,  # 불합격
            time_used=60,
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/statistics/')

        assert response.status_code == 200
        assert response.data['total_students'] == 2
        assert response.data['submitted_count'] == 2
        assert response.data['not_submitted_count'] == 0
        assert response.data['average_score'] == 10.0  # (15 + 5) / 2
        assert response.data['highest_score'] == 15
        assert response.data['lowest_score'] == 5
        assert response.data['pass_count'] == 1  # 15점만 합격
        assert response.data['fail_count'] == 1
        assert response.data['pass_rate'] == 50.0

    def test_exam_statistics_no_submissions(self, api_client, teacher_user, examination, student_user):
        """제출 없는 경우 통계"""
        ExamStudentsInfo.objects.create(exam=examination, student=student_user.studentsinfo)

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/statistics/')

        assert response.status_code == 200
        assert response.data['total_students'] == 1
        assert response.data['submitted_count'] == 0
        assert response.data['not_submitted_count'] == 1
        assert response.data['average_score'] == 0
        assert response.data['pass_count'] == 0

    def test_exam_statistics_forbidden_for_student(self, api_client, student_user, examination):
        """학생은 통계 조회 불가"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/statistics/')

        assert response.status_code == 403


@pytest.mark.django_db
class TestStudentScoreDetail:
    """개별 학생 성적 상세 조회 테스트"""

    def test_student_score_detail(self, api_client, teacher_user, examination, student_user, submitted_score):
        """개별 학생 성적 상세 조회"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/student/{student_user.studentsinfo.id}/')

        assert response.status_code == 200
        assert response.data['test_score'] == 15
        assert len(response.data['question_results']) == 2

    def test_student_score_detail_not_creator(self, api_client, another_teacher, examination, student_user):
        """시험 작성자가 아닌 교사는 조회 불가"""
        api_client.force_authenticate(user=another_teacher)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/student/{student_user.studentsinfo.id}/')

        assert response.status_code == 403

    def test_student_score_detail_not_found(self, api_client, teacher_user, examination):
        """존재하지 않는 학생 성적 조회 실패"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/v1/scores/exam/{examination.id}/student/99999/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestManualGrade:
    """수동 채점 테스트"""

    def test_manual_grade_success(
        self, api_client, teacher_user, submitted_score, multiple_choice_question
    ):
        """수동 채점 성공"""
        api_client.force_authenticate(user=teacher_user)
        data = {'question_id': multiple_choice_question.id, 'score': 7, 'comment': '부분 점수'}

        response = api_client.post(f'/api/v1/scores/{submitted_score.id}/grade/', data, format='json')

        assert response.status_code == 200
        assert '채점이 완료되었습니다' in response.data['detail']
        assert response.data['new_total_score'] == 12  # 15 - 10 + 7

        # 성적 확인
        submitted_score.refresh_from_db()
        assert submitted_score.test_score == 12
        question_id_str = str(multiple_choice_question.id)
        assert submitted_score.detail_records[question_id_str]['score'] == 7
        assert submitted_score.detail_records[question_id_str]['manual_graded'] is True

    def test_manual_grade_exceeds_max_score(
        self, api_client, teacher_user, submitted_score, multiple_choice_question
    ):
        """최대 배점 초과 실패"""
        api_client.force_authenticate(user=teacher_user)
        data = {'question_id': multiple_choice_question.id, 'score': 15}  # 최대 10점

        response = api_client.post(f'/api/v1/scores/{submitted_score.id}/grade/', data, format='json')

        assert response.status_code == 400
        assert '배점은 최대' in str(response.data)

    def test_manual_grade_forbidden_for_student(self, api_client, student_user, submitted_score):
        """학생은 수동 채점 불가"""
        api_client.force_authenticate(user=student_user)
        data = {'question_id': 1, 'score': 5}

        response = api_client.post(f'/api/v1/scores/{submitted_score.id}/grade/', data, format='json')

        assert response.status_code == 403

    def test_manual_grade_not_creator(self, api_client, another_teacher, submitted_score):
        """시험 작성자가 아닌 교사는 채점 불가"""
        api_client.force_authenticate(user=another_teacher)
        data = {'question_id': 1, 'score': 5}

        response = api_client.post(f'/api/v1/scores/{submitted_score.id}/grade/', data, format='json')

        assert response.status_code == 403

    def test_manual_grade_invalid_question(self, api_client, teacher_user, submitted_score):
        """시험지에 없는 문제 채점 실패"""
        api_client.force_authenticate(user=teacher_user)
        data = {'question_id': 99999, 'score': 5}

        response = api_client.post(f'/api/v1/scores/{submitted_score.id}/grade/', data, format='json')

        assert response.status_code == 400


@pytest.mark.django_db
class TestExceptionCases:
    """예외 상황 테스트"""

    def test_my_scores_teacher_forbidden(self, api_client, teacher_user):
        """교사는 내 성적 조회 불가 (학생 정보 없음)"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/scores/my/')

        assert response.status_code == 403
        assert '학생 정보를 찾을 수 없습니다' in response.data['detail']

    def test_my_score_detail_nonexistent_exam(self, api_client, student_user):
        """존재하지 않는 시험 조회 실패"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/v1/scores/my/99999/')

        assert response.status_code == 404

    def test_exam_scores_nonexistent_exam(self, api_client, teacher_user):
        """존재하지 않는 시험 조회 실패"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/scores/exam/99999/')

        assert response.status_code == 404

    def test_exam_statistics_nonexistent_exam(self, api_client, teacher_user):
        """존재하지 않는 시험 통계 조회 실패"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/scores/exam/99999/statistics/')

        assert response.status_code == 404

    def test_student_score_detail_nonexistent_exam(self, api_client, teacher_user):
        """존재하지 않는 시험의 학생 성적 조회 실패"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/v1/scores/exam/99999/student/1/')

        assert response.status_code == 404

    def test_manual_grade_nonexistent_score(self, api_client, teacher_user):
        """존재하지 않는 성적 채점 실패"""
        api_client.force_authenticate(user=teacher_user)
        data = {'question_id': 1, 'score': 5}

        response = api_client.post('/api/v1/scores/99999/grade/', data, format='json')

        assert response.status_code == 404
