"""
Scores API Views.
성적 조회 및 관리 API.
"""
from django.db import transaction
from django.db.models import Avg, Max, Min, Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from examination.models import ExaminationInfo, ExamStudentsInfo
from testpaper.models import TestScores, TestPaperTestQ
from testquestion.models import TestQuestionInfo

from .serializers import (
    MyScoreListSerializer,
    MyScoreDetailSerializer,
    ExamScoreListSerializer,
    ExamStatisticsSerializer,
    ManualGradeSerializer,
)


class ScoresViewSet(viewsets.ViewSet):
    """
    성적 조회 및 관리 ViewSet.

    학생: 내 성적 조회
    교사: 시험별 성적 조회, 통계, 수동 채점
    """

    permission_classes = [IsAuthenticated]

    def get_student_info(self, user):
        """사용자의 학생 정보 조회"""
        try:
            return user.studentsinfo
        except Exception:
            return None

    @action(detail=False, methods=['get'], url_path='my')
    def my_scores(self, request):
        """
        내 성적 목록 조회 (학생용).
        GET /api/v1/scores/my/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 제출한 성적만 조회
        scores = TestScores.objects.filter(user=student_info, is_submitted=True).select_related(
            'exam', 'exam__subject', 'test_paper'
        ).order_by('-submit_time')

        serializer = MyScoreListSerializer(scores, many=True)
        return Response({'scores': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='my/(?P<exam_id>[^/.]+)')
    def my_score_detail(self, request, exam_id=None):
        """
        내 성적 상세 조회 (학생용).
        GET /api/v1/scores/my/{exam_id}/
        """
        student_info = self.get_student_info(request.user)
        if not student_info:
            return Response({'detail': '학생 정보를 찾을 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=exam_id)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 성적 조회
        try:
            score = TestScores.objects.select_related('exam', 'exam__subject', 'test_paper').get(
                exam=exam, user=student_info, is_submitted=True
            )
        except TestScores.DoesNotExist:
            return Response({'detail': '제출한 성적이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MyScoreDetailSerializer(score)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='exam/(?P<exam_id>[^/.]+)')
    def exam_scores(self, request, exam_id=None):
        """
        시험별 성적 목록 조회 (교사용).
        GET /api/v1/scores/exam/{exam_id}/
        """
        if request.user.user_type != 'teacher':
            return Response({'detail': '교사만 접근할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=exam_id)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 시험 작성자만 조회 가능
        if exam.create_user != request.user:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 시험 등록된 모든 학생의 성적 조회
        scores = TestScores.objects.filter(exam=exam).select_related('user', 'test_paper').order_by(
            '-is_submitted', '-test_score'
        )

        serializer = ExamScoreListSerializer(scores, many=True)
        return Response({'exam_id': exam.id, 'exam_name': exam.name, 'scores': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='exam/(?P<exam_id>[^/.]+)/statistics')
    def exam_statistics(self, request, exam_id=None):
        """
        시험 성적 통계 조회 (교사용).
        GET /api/v1/scores/exam/{exam_id}/statistics/
        """
        if request.user.user_type != 'teacher':
            return Response({'detail': '교사만 접근할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=exam_id)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 시험 작성자만 조회 가능
        if exam.create_user != request.user:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 통계 계산
        total_students = ExamStudentsInfo.objects.filter(exam=exam).count()
        scores = TestScores.objects.filter(exam=exam, is_submitted=True)

        submitted_count = scores.count()
        not_submitted_count = total_students - submitted_count

        if submitted_count == 0:
            data = {
                'exam_id': exam.id,
                'exam_name': exam.name,
                'total_students': total_students,
                'submitted_count': 0,
                'not_submitted_count': not_submitted_count,
                'average_score': 0,
                'highest_score': 0,
                'lowest_score': 0,
                'pass_count': 0,
                'fail_count': 0,
                'pass_rate': 0.0,
            }
        else:
            stats = scores.aggregate(avg_score=Avg('test_score'), max_score=Max('test_score'), min_score=Min('test_score'))

            # 합격/불합격 수 계산
            paper = exam.exampaperinfo_set.first().paper if exam.exampaperinfo_set.exists() else None
            if paper:
                pass_count = scores.filter(test_score__gte=paper.passing_score).count()
                fail_count = submitted_count - pass_count
                pass_rate = (pass_count / submitted_count * 100) if submitted_count > 0 else 0
            else:
                pass_count = 0
                fail_count = 0
                pass_rate = 0.0

            data = {
                'exam_id': exam.id,
                'exam_name': exam.name,
                'total_students': total_students,
                'submitted_count': submitted_count,
                'not_submitted_count': not_submitted_count,
                'average_score': round(stats['avg_score'], 2) if stats['avg_score'] else 0,
                'highest_score': stats['max_score'] or 0,
                'lowest_score': stats['min_score'] or 0,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': round(pass_rate, 2),
            }

        serializer = ExamStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='exam/(?P<exam_id>[^/.]+)/student/(?P<student_id>[^/.]+)')
    def student_score_detail(self, request, exam_id=None, student_id=None):
        """
        개별 학생 성적 상세 조회 (교사용).
        GET /api/v1/scores/exam/{exam_id}/student/{student_id}/
        """
        if request.user.user_type != 'teacher':
            return Response({'detail': '교사만 접근할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            exam = ExaminationInfo.objects.get(id=exam_id)
        except ExaminationInfo.DoesNotExist:
            return Response({'detail': '시험을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 시험 작성자만 조회 가능
        if exam.create_user != request.user:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 학생 성적 조회
        try:
            score = TestScores.objects.select_related('exam', 'exam__subject', 'test_paper', 'user').get(
                exam=exam, user_id=student_id
            )
        except TestScores.DoesNotExist:
            return Response({'detail': '성적을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MyScoreDetailSerializer(score)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='grade')
    def manual_grade(self, request, pk=None):
        """
        수동 채점 (교사용).
        POST /api/v1/scores/{score_id}/grade/
        """
        if request.user.user_type != 'teacher':
            return Response({'detail': '교사만 접근할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            score = TestScores.objects.select_related('exam', 'test_paper').get(id=pk)
        except TestScores.DoesNotExist:
            return Response({'detail': '성적을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 시험 작성자만 채점 가능
        if score.exam and score.exam.create_user != request.user:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ManualGradeSerializer(data=request.data, context={'test_score': score})
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data['question_id']
        new_score = serializer.validated_data['score']
        comment = serializer.validated_data.get('comment', '')

        # detail_records 업데이트
        with transaction.atomic():
            if not score.detail_records:
                score.detail_records = {}

            question_id_str = str(question_id)
            if question_id_str not in score.detail_records:
                score.detail_records[question_id_str] = {}

            # 기존 점수 차감
            old_score = score.detail_records[question_id_str].get('score', 0)
            score.detail_records[question_id_str]['score'] = new_score
            score.detail_records[question_id_str]['manual_graded'] = True
            if comment:
                score.detail_records[question_id_str]['comment'] = comment

            # 총점 재계산
            score.test_score = score.test_score - old_score + new_score
            score.save()

        return Response(
            {'detail': '채점이 완료되었습니다.', 'new_total_score': score.test_score}, status=status.HTTP_200_OK
        )
