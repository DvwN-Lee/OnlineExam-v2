"""
Exam Taking API Tests.
시험 응시 관련 API 테스트.
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
        username='teacher_taking', password='testpass123', user_type='teacher', nick_name='Taking Teacher'
    )


@pytest.fixture
def student_user(db):
    user = UserProfile.objects.create_user(
        username='student_taking', password='testpass123', user_type='student', nick_name='Taking Student'
    )
    StudentsInfo.objects.create(
        user=user,
        student_name='Taking Student',
        student_id='20250101',
        student_class='1-A',
        student_school='Test School',
    )
    return user


@pytest.fixture
def another_student(db):
    user = UserProfile.objects.create_user(
        username='student2', password='testpass123', user_type='student', nick_name='Student 2'
    )
    StudentsInfo.objects.create(
        user=user, student_name='Student 2', student_id='20250102', student_class='1-B', student_school='Test School'
    )
    return user


@pytest.fixture
def subject(db):
    return SubjectInfo.objects.create(subject_name='Taking Subject')


@pytest.fixture
def multiple_choice_question(db, teacher_user, subject):
    """객관식 문제 생성"""
    question = TestQuestionInfo.objects.create(
        name='What is 2+2?',
        subject=subject,
        score=10,
        tq_type='xz',  # 객관식
        tq_degree='jd',
        create_user=teacher_user,
    )
    # 선택지 생성
    OptionInfo.objects.create(test_question=question, option='3', is_right=False)
    OptionInfo.objects.create(test_question=question, option='4', is_right=True)  # 정답
    OptionInfo.objects.create(test_question=question, option='5', is_right=False)
    return question


@pytest.fixture
def true_false_question(db, teacher_user, subject):
    """OX 문제 생성"""
    question = TestQuestionInfo.objects.create(
        name='Python is a programming language',
        subject=subject,
        score=5,
        tq_type='pd',  # OX
        tq_degree='jd',
        create_user=teacher_user,
    )
    OptionInfo.objects.create(test_question=question, option='True', is_right=True)
    OptionInfo.objects.create(test_question=question, option='False', is_right=False)
    return question


@pytest.fixture
def test_paper(db, teacher_user, subject, multiple_choice_question, true_false_question):
    """시험지 생성 및 문제 연결"""
    paper = TestPaperInfo.objects.create(
        name='Taking Test Paper',
        subject=subject,
        tp_degree='jd',
        total_score=15,
        passing_score=9,
        question_count=2,
        create_user=teacher_user,
    )
    # 문제 연결
    TestPaperTestQ.objects.create(test_paper=paper, test_question=multiple_choice_question, score=10, order=1)
    TestPaperTestQ.objects.create(test_paper=paper, test_question=true_false_question, score=5, order=2)
    return paper


@pytest.fixture
def ongoing_examination(db, teacher_user, subject, test_paper):
    """현재 진행 중인 시험"""
    now = timezone.now()
    exam = ExaminationInfo.objects.create(
        name='Ongoing Exam',
        subject=subject,
        start_time=now - timedelta(minutes=10),  # 10분 전 시작
        end_time=now + timedelta(hours=1),  # 1시간 후 종료
        exam_state='1',  # 진행 중
        exam_type='pt',
        student_num=0,
        actual_num=0,
        create_user=teacher_user,
    )
    ExamPaperInfo.objects.create(exam=exam, paper=test_paper)
    return exam


@pytest.fixture
def future_examination(db, teacher_user, subject, test_paper):
    """미래 시험"""
    start_time = timezone.now() + timedelta(days=1)
    exam = ExaminationInfo.objects.create(
        name='Future Exam',
        subject=subject,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        exam_state='0',
        exam_type='pt',
        student_num=0,
        actual_num=0,
        create_user=teacher_user,
    )
    ExamPaperInfo.objects.create(exam=exam, paper=test_paper)
    return exam


@pytest.fixture
def past_examination(db, teacher_user, subject, test_paper):
    """종료된 시험"""
    end_time = timezone.now() - timedelta(hours=1)
    exam = ExaminationInfo.objects.create(
        name='Past Exam',
        subject=subject,
        start_time=end_time - timedelta(hours=2),
        end_time=end_time,
        exam_state='2',  # 종료
        exam_type='pt',
        student_num=0,
        actual_num=0,
        create_user=teacher_user,
    )
    ExamPaperInfo.objects.create(exam=exam, paper=test_paper)
    return exam


@pytest.mark.django_db
class TestExamInfo:
    """시험 정보 조회 테스트"""

    def test_get_exam_info_success(self, api_client, student_user, ongoing_examination):
        """등록된 학생이 시험 정보 조회 성공"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/taking/{ongoing_examination.id}/info/')

        assert response.status_code == 200
        assert response.data['exam_name'] == 'Ongoing Exam'
        assert response.data['question_count'] == 2
        assert len(response.data['questions']) == 2
        assert response.data['total_score'] == 15
        assert response.data['passing_score'] == 9
        # 정답 정보는 포함되지 않아야 함
        for question in response.data['questions']:
            assert 'options' in question
            for option in question['options']:
                assert 'is_right' not in option

    def test_get_exam_info_not_enrolled_fails(self, api_client, student_user, ongoing_examination):
        """등록되지 않은 학생이 시험 정보 조회 실패"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/taking/{ongoing_examination.id}/info/')

        assert response.status_code == 403
        assert '등록되지 않았습니다' in response.data['detail']

    def test_get_exam_info_no_student_info(self, api_client, teacher_user, ongoing_examination):
        """학생 정보가 없는 사용자 조회 실패"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get(f'/api/v1/taking/{ongoing_examination.id}/info/')

        assert response.status_code == 403
        assert '학생 정보를 찾을 수 없습니다' in response.data['detail']

    def test_get_exam_info_not_found(self, api_client, student_user):
        """존재하지 않는 시험 조회 실패"""
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/v1/taking/99999/info/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestExamStart:
    """시험 시작 테스트"""

    def test_start_exam_success(self, api_client, student_user, ongoing_examination):
        """정상적인 시험 시작"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/start/')

        assert response.status_code == 200
        assert '시작되었습니다' in response.data['detail']
        assert 'start_time' in response.data
        assert 'end_time' in response.data

        # TestScores 기록 확인
        test_score = TestScores.objects.filter(exam=ongoing_examination, user=student_info).first()
        assert test_score is not None
        assert test_score.start_time is not None
        assert not test_score.is_submitted

    def test_start_exam_before_start_time_fails(self, api_client, student_user, future_examination):
        """시작 시간 전 시험 시작 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=future_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/v1/taking/{future_examination.id}/start/')

        assert response.status_code == 400
        assert '시작 시간이 아닙니다' in response.data['detail']

    def test_start_exam_after_end_time_fails(self, api_client, student_user, past_examination):
        """종료 시간 후 시험 시작 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=past_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/v1/taking/{past_examination.id}/start/')

        assert response.status_code == 400
        assert '종료 시간이 지났습니다' in response.data['detail']

    def test_start_exam_not_enrolled_fails(self, api_client, student_user, ongoing_examination):
        """등록되지 않은 학생의 시험 시작 실패"""
        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/start/')

        assert response.status_code == 403

    def test_start_exam_already_started(self, api_client, student_user, ongoing_examination):
        """이미 시작한 시험 재시작 시도"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        # 첫 번째 시작
        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now(),
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/start/')

        assert response.status_code == 200
        assert '이미 시작한 시험입니다' in response.data['detail']

    def test_start_exam_already_submitted_fails(self, api_client, student_user, ongoing_examination):
        """이미 제출한 시험 재시작 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=30),
            submit_time=timezone.now() - timedelta(minutes=5),
            is_submitted=True,
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/start/')

        assert response.status_code == 400
        assert '이미 제출한 시험입니다' in response.data['detail']


@pytest.mark.django_db
class TestExamSubmit:
    """답안 제출 및 자동 채점 테스트"""

    def test_submit_answers_correct(
        self, api_client, student_user, ongoing_examination, multiple_choice_question, true_false_question
    ):
        """정답 제출 및 자동 채점"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        # 시험 시작
        test_score = TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=10),
        )

        # 정답 ID 찾기
        correct_mc_option = OptionInfo.objects.get(test_question=multiple_choice_question, is_right=True)
        correct_tf_option = OptionInfo.objects.get(test_question=true_false_question, is_right=True)

        api_client.force_authenticate(user=student_user)
        data = {
            'answers': [
                {'question_id': multiple_choice_question.id, 'answer': str(correct_mc_option.id)},
                {'question_id': true_false_question.id, 'answer': str(correct_tf_option.id)},
            ]
        }

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/submit/', data, format='json')

        assert response.status_code == 200
        assert response.data['score'] == 15  # 만점
        assert response.data['total_possible'] == 15
        assert response.data['passed'] is True
        assert 'time_used' in response.data

        # TestScores 확인
        test_score.refresh_from_db()
        assert test_score.is_submitted
        assert test_score.test_score == 15
        assert test_score.submit_time is not None

    def test_submit_answers_incorrect(
        self, api_client, student_user, ongoing_examination, multiple_choice_question, true_false_question
    ):
        """오답 제출 및 자동 채점"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=10),
        )

        # 오답 ID 찾기
        wrong_mc_option = OptionInfo.objects.filter(test_question=multiple_choice_question, is_right=False).first()
        wrong_tf_option = OptionInfo.objects.filter(test_question=true_false_question, is_right=False).first()

        api_client.force_authenticate(user=student_user)
        data = {
            'answers': [
                {'question_id': multiple_choice_question.id, 'answer': str(wrong_mc_option.id)},
                {'question_id': true_false_question.id, 'answer': str(wrong_tf_option.id)},
            ]
        }

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/submit/', data, format='json')

        assert response.status_code == 200
        assert response.data['score'] == 0  # 0점
        assert response.data['passed'] is False

    def test_submit_answers_partial(
        self, api_client, student_user, ongoing_examination, multiple_choice_question, true_false_question
    ):
        """일부 정답 제출"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=10),
        )

        correct_mc_option = OptionInfo.objects.get(test_question=multiple_choice_question, is_right=True)
        wrong_tf_option = OptionInfo.objects.get(test_question=true_false_question, is_right=False)

        api_client.force_authenticate(user=student_user)
        data = {
            'answers': [
                {'question_id': multiple_choice_question.id, 'answer': str(correct_mc_option.id)},  # 정답
                {'question_id': true_false_question.id, 'answer': str(wrong_tf_option.id)},  # 오답
            ]
        }

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/submit/', data, format='json')

        assert response.status_code == 200
        assert response.data['score'] == 10  # 첫 문제만 정답
        assert response.data['passed'] is True  # 합격점(9점) 이상

    def test_submit_without_starting_fails(self, api_client, student_user, ongoing_examination):
        """시작하지 않은 시험 제출 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        data = {'answers': [{'question_id': 1, 'answer': '1'}]}

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/submit/', data, format='json')

        assert response.status_code == 400
        assert '시작하지 않았습니다' in response.data['detail']

    def test_submit_already_submitted_fails(self, api_client, student_user, ongoing_examination):
        """이미 제출한 시험 재제출 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=30),
            submit_time=timezone.now() - timedelta(minutes=5),
            is_submitted=True,
        )

        api_client.force_authenticate(user=student_user)
        data = {'answers': [{'question_id': 1, 'answer': '1'}]}

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/submit/', data, format='json')

        assert response.status_code == 400
        assert '이미 제출한 시험입니다' in response.data['detail']


@pytest.mark.django_db
class TestExamStatus:
    """응시 상태 조회 테스트"""

    def test_status_before_start(self, api_client, student_user, ongoing_examination):
        """시작 전 상태 조회"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/taking/{ongoing_examination.id}/status/')

        assert response.status_code == 200
        assert response.data['is_started'] is False
        assert response.data['is_submitted'] is False
        assert response.data['start_time'] is None
        assert response.data['score'] is None

    def test_status_after_start(self, api_client, student_user, ongoing_examination):
        """시작 후 상태 조회"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=10),
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/taking/{ongoing_examination.id}/status/')

        assert response.status_code == 200
        assert response.data['is_started'] is True
        assert response.data['is_submitted'] is False
        assert response.data['start_time'] is not None
        assert response.data['time_remaining'] is not None
        assert response.data['time_remaining'] > 0

    def test_status_after_submit(self, api_client, student_user, ongoing_examination):
        """제출 후 상태 조회"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=30),
            submit_time=timezone.now() - timedelta(minutes=5),
            is_submitted=True,
            test_score=15,
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/v1/taking/{ongoing_examination.id}/status/')

        assert response.status_code == 200
        assert response.data['is_submitted'] is True
        assert response.data['score'] == 15
        assert response.data['draft_answers'] is None  # 제출 후에는 draft 없음


@pytest.mark.django_db
class TestSaveDraft:
    """답안 임시 저장 테스트"""

    def test_save_draft_success(self, api_client, student_user, ongoing_examination):
        """정상적인 임시 저장"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=10),
        )

        api_client.force_authenticate(user=student_user)
        data = {'answers': {'1': {'answer': 'draft answer 1'}, '2': {'answer': 'draft answer 2'}}}

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/save-draft/', data, format='json')

        assert response.status_code == 200
        assert '임시 저장되었습니다' in response.data['detail']

        # TestScores 확인
        test_score = TestScores.objects.get(exam=ongoing_examination, user=student_info)
        assert test_score.detail_records == data['answers']

    def test_save_draft_without_starting_fails(self, api_client, student_user, ongoing_examination):
        """시작하지 않은 시험 임시 저장 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        api_client.force_authenticate(user=student_user)
        data = {'answers': {'1': {'answer': 'draft'}}}

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/save-draft/', data, format='json')

        assert response.status_code == 400
        assert '시작하지 않았습니다' in response.data['detail']

    def test_save_draft_after_submit_fails(self, api_client, student_user, ongoing_examination):
        """제출 후 임시 저장 실패"""
        student_info = student_user.studentsinfo
        ExamStudentsInfo.objects.create(exam=ongoing_examination, student=student_info)

        TestScores.objects.create(
            exam=ongoing_examination,
            user=student_info,
            test_paper=ongoing_examination.exampaperinfo_set.first().paper,
            start_time=timezone.now() - timedelta(minutes=30),
            is_submitted=True,
        )

        api_client.force_authenticate(user=student_user)
        data = {'answers': {'1': {'answer': 'draft'}}}

        response = api_client.post(f'/api/v1/taking/{ongoing_examination.id}/save-draft/', data, format='json')

        assert response.status_code == 400
        assert '이미 제출한 시험입니다' in response.data['detail']
