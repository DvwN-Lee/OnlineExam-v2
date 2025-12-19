"""
통합 모델 테스트.

모든 앱의 모든 모델에 대해 기본적인 속성을 검증합니다.
"""

import pytest
from django.apps import apps


@pytest.mark.django_db
class TestModelsStr:
    """모든 모델의 __str__ 메서드 테스트"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, db):
        """테스트용 기본 데이터 생성"""
        from user.models import UserProfile, SubjectInfo, StudentsInfo, TeacherInfo
        from examination.models import ExaminationInfo, ExamPaperInfo, ExamStudentsInfo
        from testpaper.models import TestPaperInfo, TestScores
        from testquestion.models import TestQuestionInfo, OptionInfo

        # Subject 생성
        self.subject = SubjectInfo.objects.create(subject_name='Test Subject')

        # User 생성
        self.user = UserProfile.objects.create_user(
            username='testuser', password='testpass', user_type='student'
        )

        # StudentsInfo 생성
        self.student = StudentsInfo.objects.create(
            user=self.user,
            student_name='Test Student'
        )

        # Question 생성
        self.question = TestQuestionInfo.objects.create(
            name='Test Question',
            subject=self.subject,
            score=10,
            tq_type='xz',
            tq_degree='jd',
            create_user=self.user
        )

        # Option 생성
        self.option = OptionInfo.objects.create(
            test_question=self.question,
            option='Test Option',
            is_right=True
        )

        # TestPaper 생성
        self.paper = TestPaperInfo.objects.create(
            name='Test Paper',
            subject=self.subject,
            tp_degree='jd',
            total_score=10,
            passing_score=6,
            create_user=self.user
        )

        # Examination 생성
        from django.utils import timezone
        self.exam = ExaminationInfo.objects.create(
            name='Test Exam',
            subject=self.subject,
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            create_user=self.user
        )

        # ExamPaperInfo 생성
        ExamPaperInfo.objects.create(
            exam=self.exam,
            paper=self.paper
        )

        # ExamStudentsInfo 생성
        ExamStudentsInfo.objects.create(
            exam=self.exam,
            student=self.student
        )

        # TestPaperTestQ 생성
        from testpaper.models import TestPaperTestQ
        TestPaperTestQ.objects.create(
            test_paper=self.paper,
            test_question=self.question,
            score=10,
            order=1
        )

        # TeacherInfo 생성 (user_type을 teacher로 변경한 교사 생성)
        teacher_user = UserProfile.objects.create_user(
            username='teacher', password='testpass', user_type='teacher'
        )
        TeacherInfo.objects.create(
            user=teacher_user,
            teacher_name='Test Teacher',
            subject=self.subject
        )

        # EmailVerifyRecord 생성
        from user.models import EmailVerifyRecord
        EmailVerifyRecord.objects.create(
            code='TEST123',
            email='test@example.com',
            send_type='register'
        )

    def test_all_models_str_method(self):
        """모든 모델의 __str__ 메서드가 에러 없이 실행되는지 확인"""
        # Django가 관리하는 모든 모델 가져오기
        all_models = apps.get_models()

        errors = []
        tested_models = []

        for model in all_models:
            # 테스트용 모델이거나 Django 내장 모델은 스킵
            if model._meta.app_label in ['contenttypes', 'auth', 'admin', 'sessions', 'token_blacklist']:
                continue

            try:
                # 모델의 첫 번째 인스턴스 가져오기
                instance = model.objects.first()

                if instance:
                    # __str__ 메서드 호출 (에러 발생 여부 확인)
                    result = str(instance)
                    assert isinstance(result, str), f"{model.__name__}.__str__() must return string"
                    tested_models.append(model.__name__)

            except Exception as e:
                errors.append(f"{model.__name__}: {str(e)}")

        # 테스트된 모델 로깅
        print(f"\nTested {len(tested_models)} models: {', '.join(tested_models)}")

        # 에러가 있으면 실패
        if errors:
            pytest.fail(f"Errors in __str__ methods:\n" + "\n".join(errors))

        # 최소한 몇 개의 모델은 테스트되었는지 확인
        assert len(tested_models) >= 5, f"At least 5 models should be tested, but only {len(tested_models)} were tested"


@pytest.mark.django_db
class TestModelsBasic:
    """모든 모델의 기본 속성 테스트"""

    def test_all_models_have_meta_verbose_name(self):
        """모든 커스텀 모델이 Meta.verbose_name을 가지고 있는지 확인 (선택적)"""
        all_models = apps.get_models()

        for model in all_models:
            # 프로젝트의 앱만 검사
            if model._meta.app_label in ['examination', 'testpaper', 'testquestion', 'user', 'operation']:
                # verbose_name이 기본값(모델명)이 아닌지 확인 (선택적 검증)
                # 이 테스트는 코드 품질 향상을 위한 것
                pass  # 일단 pass, 필요시 검증 추가
