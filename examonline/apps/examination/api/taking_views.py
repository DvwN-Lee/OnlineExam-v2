"""
Exam Taking API Views.
학생의 시험 응시 관련 API.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from examination.models import ExaminationInfo, ExamPaperInfo, ExamStudentsInfo
from testpaper.models import TestScores, TestPaperTestQ
from testquestion.models import TestQuestionInfo, OptionInfo

from .serializers import (
    ExamInfoSerializer,
    AnswerSubmissionSerializer,
    ExamStatusSerializer,
    SaveDraftSerializer,
    ExamQuestionSerializer,
)


class ExamTakingViewSet(viewsets.ViewSet):
    """
    시험 응시 ViewSet.

    학생이 시험을 응시하고 답안을 제출하는 기능.
    """

    permission_classes = [IsAuthenticated]

    def get_student_info(self, user):
        """사용자의 학생 정보 조회"""
        try:
            return user.studentsinfo
        except Exception:
            return None

    @action(detail=True, methods=['get'], url_path='info')
    def exam_info(self, request, pk=None):
        """
        시험 정보 및 문제 조회.
        GET /api/v1/taking/{exam_id}/info/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.select_related('subject').get(id=pk)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 응시 자격 확인
        if not ExamStudentsInfo.objects.filter(exam=exam, student=student_info).exists():
            return Response({'detail': '이 시험에 등록되지 않았습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 시험지 조회
        exam_papers = ExamPaperInfo.objects.filter(exam=exam).select_related('paper')
        if not exam_papers.exists():
            return Response({'detail': '시험지가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 첫 번째 시험지 사용 (추후 다중 시험지 지원 가능)
        paper = exam_papers.first().paper

        # 문제 조회
        paper_questions = TestPaperTestQ.objects.filter(test_paper=paper).select_related(
            'test_question'
        ).prefetch_related('test_question__optioninfo_set').order_by('order')

        questions = [pq.test_question for pq in paper_questions]

        # 응시 상태 확인
        test_score = TestScores.objects.filter(exam=exam, user=student_info).first()
        is_started = test_score is not None and test_score.start_time is not None
        is_submitted = test_score is not None and test_score.is_submitted

        # 시험 정보 구성
        duration = int((exam.end_time - exam.start_time).total_seconds() / 60)

        data = {
            'exam_id': exam.id,
            'exam_name': exam.name,
            'subject_name': exam.subject.subject_name,
            'start_time': exam.start_time,
            'end_time': exam.end_time,
            'duration': duration,
            'total_score': paper.total_score,
            'passing_score': paper.passing_score,
            'question_count': paper.question_count,
            'questions': ExamQuestionSerializer(
                questions, many=True, context={'paper_id': paper.id}
            ).data,
            'is_started': is_started,
            'is_submitted': is_submitted,
        }

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        시험 시작.
        POST /api/v1/taking/{exam_id}/start/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=pk)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 응시 자격 확인
        if not ExamStudentsInfo.objects.filter(exam=exam, student=student_info).exists():
            return Response({'detail': '이 시험에 등록되지 않았습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 시험 시간 확인
        now = timezone.now()
        if now < exam.start_time:
            return Response({'detail': '아직 시험 시작 시간이 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if now > exam.end_time:
            return Response({'detail': '시험 종료 시간이 지났습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 시작한 경우
        existing_score = TestScores.objects.filter(exam=exam, user=student_info).first()
        if existing_score and existing_score.start_time:
            if existing_score.is_submitted:
                return Response({'detail': '이미 제출한 시험입니다.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {
                    'detail': '이미 시작한 시험입니다.',
                    'start_time': existing_score.start_time,
                },
                status=status.HTTP_200_OK,
            )

        # 시험지 조회
        exam_paper = ExamPaperInfo.objects.filter(exam=exam).first()
        if not exam_paper:
            return Response({'detail': '시험지가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 시험 시작 기록
        with transaction.atomic():
            if existing_score:
                existing_score.start_time = now
                existing_score.save()
                test_score = existing_score
            else:
                test_score = TestScores.objects.create(
                    exam=exam,
                    user=student_info,
                    test_paper=exam_paper.paper,
                    start_time=now,
                    test_score=0,
                    detail_records={},
                )

        return Response(
            {
                'detail': '시험이 시작되었습니다.',
                'start_time': test_score.start_time,
                'end_time': exam.end_time,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        답안 제출 및 자동 채점.
        POST /api/v1/taking/{exam_id}/submit/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=pk)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AnswerSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers = serializer.validated_data['answers']

        # 시험 기록 조회
        test_score = TestScores.objects.filter(exam=exam, user=student_info).first()
        if not test_score or not test_score.start_time:
            return Response({'detail': '시험을 시작하지 않았습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if test_score.is_submitted:
            return Response({'detail': '이미 제출한 시험입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 제한 시간 확인
        now = timezone.now()
        if now > exam.end_time:
            # 자동 제출 처리
            pass

        # 자동 채점
        total_score = 0
        detailed_records = {}

        for answer_item in answers:
            question_id = answer_item['question_id']
            user_answer = answer_item.get('answer', '')

            try:
                question = TestQuestionInfo.objects.get(id=question_id)
                paper_question = TestPaperTestQ.objects.get(
                    test_paper=test_score.test_paper, test_question=question
                )
                question_score = paper_question.score

                # 채점
                is_correct = False
                if question.tq_type in ['xz', 'pd']:  # 객관식, OX
                    try:
                        correct_option = OptionInfo.objects.get(test_question=question, is_right=True)
                        is_correct = str(user_answer) == str(correct_option.id)
                    except OptionInfo.DoesNotExist:
                        is_correct = False

                earned_score = question_score if is_correct else 0
                total_score += earned_score

                detailed_records[str(question_id)] = {
                    'answer': user_answer,
                    'is_correct': is_correct,
                    'score': earned_score,
                    'max_score': question_score,
                }

            except (TestQuestionInfo.DoesNotExist, TestPaperTestQ.DoesNotExist):
                continue

        # 소요 시간 계산
        time_used = int((now - test_score.start_time).total_seconds() / 60)

        # 제출 기록
        with transaction.atomic():
            test_score.test_score = total_score
            test_score.detail_records = detailed_records
            test_score.submit_time = now
            test_score.is_submitted = True
            test_score.time_used = time_used
            test_score.save()

        return Response(
            {
                'detail': '답안이 제출되었습니다.',
                'score': total_score,
                'total_possible': test_score.test_paper.total_score,
                'passed': total_score >= test_score.test_paper.passing_score,
                'time_used': time_used,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        응시 상태 조회.
        GET /api/v1/taking/{exam_id}/status/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=pk)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        test_score = TestScores.objects.filter(exam=exam, user=student_info).first()

        if not test_score:
            data = {
                'exam_id': exam.id,
                'exam_name': exam.name,
                'is_started': False,
                'is_submitted': False,
                'start_time': None,
                'submit_time': None,
                'time_remaining': None,
                'draft_answers': None,
                'score': None,
            }
        else:
            time_remaining = None
            if test_score.start_time and not test_score.is_submitted:
                now = timezone.now()
                remaining_seconds = (exam.end_time - now).total_seconds()
                time_remaining = max(0, int(remaining_seconds / 60))

            data = {
                'exam_id': exam.id,
                'exam_name': exam.name,
                'is_started': test_score.start_time is not None,
                'is_submitted': test_score.is_submitted,
                'start_time': test_score.start_time,
                'submit_time': test_score.submit_time,
                'time_remaining': time_remaining,
                'draft_answers': test_score.detail_records if not test_score.is_submitted else None,
                'score': test_score.test_score if test_score.is_submitted else None,
            }

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='save-draft')
    def save_draft(self, request, pk=None):
        """
        답안 임시 저장.
        POST /api/v1/taking/{exam_id}/save-draft/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=pk)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SaveDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_score = TestScores.objects.filter(exam=exam, user=student_info).first()
        if not test_score or not test_score.start_time:
            return Response({'detail': '시험을 시작하지 않았습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if test_score.is_submitted:
            return Response({'detail': '이미 제출한 시험입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 임시 저장
        test_score.detail_records = serializer.validated_data['answers']
        test_score.save()

        return Response(
            {'detail': '임시 저장되었습니다.', 'saved_at': timezone.now()}, status=status.HTTP_200_OK
        )
