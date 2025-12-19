# ExamOnline

Django 기반 온라인 시험 관리 시스템

## 기술 스택

- Backend: Django 5.2 LTS, Python 3.14
- Primary DB: PostgreSQL 18
- Secondary DB: MongoDB 8.0
- Cache: Redis 8.0
- Frontend: React 19 + TypeScript 6.x + Vite 6.x

## 개발 환경 설정

### 필수 요구사항

- Python 3.14+
- uv (패키지 관리자)
- Docker & Docker Compose

### 설치

```bash
# 의존성 설치
uv sync

# 개발 의존성 포함 설치
uv sync --all-extras

# 가상환경 활성화
source .venv/bin/activate
```

### 개발 서버 실행

```bash
# DB 컨테이너 시작
docker compose -f docker-compose.dev.yml up -d

# Django 개발 서버
uv run python manage.py runserver
```

## 프로젝트 구조

```
examonline/
├── apps/                   # Django 앱
│   ├── examination/        # 시험 관리
│   ├── testpaper/          # 시험지 관리
│   ├── testquestion/       # 문제 관리
│   ├── user/               # 사용자 관리
│   └── operation/          # 운영 기능
├── config/                 # 환경별 설정
├── docker/                 # Docker 설정
├── docs/                   # 문서
└── manage.py
```

## 개발 현황

### Backend API 개발 상세 단계

**Phase 1-2: Foundation** (완료)
- 1.1 Django 5.2 + DRF 설정
- 1.2 PostgreSQL, MongoDB, Redis 연동
- 2.1 JWT 인증 구현
- 2.2 역할 기반 권한 (IsTeacher, IsStudent)
- 2.3 사용자 관리 API (회원가입, 로그인, 프로필)

**Phase 3: Question Management API** (완료 - Issues #1-4)
- 3.1 Question CRUD
- 3.2 필터링 및 검색
- 3.3 문제 공유 기능
- 3.4 문제 은행 관리
- Coverage: 98%

**Phase 4: Examination System API** (완료 - Issues #5-8)
- 4.1 TestPaper Management
- 4.2 Examination Scheduling
- 4.3 Exam Taking
- 4.4 Scores & Grading
- Coverage: 92-97%

**향후 Backend 고도화 계획**
- Statistics & Analytics API
- Real-time notifications
- Advanced reporting

### Test Coverage

- **전체 Coverage**: 97.44%
- **총 테스트 수**: 141개
- **모든 테스트 통과**: 100%

상세 내역:
- examination API: 86-94%
- testpaper API: 93-97%
- testquestion API: 91-98%
- user API: 99-100%
- models: 95-100%

## 테스트 실행

```bash
# 전체 테스트 실행
uv run pytest

# Coverage 리포트 생성
uv run pytest apps/ --cov=apps --cov-report=term --cov-report=html

# 특정 앱 테스트
uv run pytest apps/user/
uv run pytest apps/testpaper/

# HTML 리포트 확인
open htmlcov/index.html
```

## API 문서

구현된 API endpoint:

### 사용자 관리
- `POST /api/v1/auth/register/` - 회원가입
- `POST /api/v1/auth/token/` - 로그인
- `POST /api/v1/auth/token/refresh/` - Token 갱신
- `GET /api/v1/users/me/` - 프로필 조회
- `PATCH /api/v1/users/me/` - 프로필 수정
- `PUT /api/v1/users/me/change-password/` - 비밀번호 변경

### 과목 관리
- `GET /api/v1/subjects/` - 과목 목록
- `POST /api/v1/subjects/` - 과목 생성 (교사)
- `PATCH /api/v1/subjects/{id}/` - 과목 수정 (교사)
- `DELETE /api/v1/subjects/{id}/` - 과목 삭제 (교사)

### 문제 관리
- `GET /api/v1/questions/` - 문제 목록
- `POST /api/v1/questions/` - 문제 생성 (교사)
- `GET /api/v1/questions/{id}/` - 문제 상세
- `PATCH /api/v1/questions/{id}/` - 문제 수정 (작성자)
- `DELETE /api/v1/questions/{id}/` - 문제 삭제 (작성자)
- `POST /api/v1/questions/{id}/share/` - 문제 공유 (작성자)
- `GET /api/v1/questions/my/` - 내 문제 목록 (교사)
- `GET /api/v1/questions/shared/` - 공유 문제 목록

### 시험지 관리
- `GET /api/v1/papers/` - 시험지 목록
- `POST /api/v1/papers/` - 시험지 생성 (교사)
- `GET /api/v1/papers/{id}/` - 시험지 상세
- `PATCH /api/v1/papers/{id}/` - 시험지 수정 (작성자)
- `DELETE /api/v1/papers/{id}/` - 시험지 삭제 (작성자)
- `POST /api/v1/papers/{id}/add_questions/` - 문제 추가 (작성자)
- `DELETE /api/v1/papers/{id}/remove-question/{question_id}/` - 문제 제거 (작성자)
- `GET /api/v1/papers/{id}/preview/` - 시험지 미리보기

### 성적 관리
- `GET /api/v1/scores/my/` - 내 성적 목록 (학생)
- `GET /api/v1/scores/my/{exam_id}/` - 특정 시험 성적 (학생)
- `GET /api/v1/scores/exam/{exam_id}/` - 시험별 성적 목록 (교사)
- `POST /api/v1/scores/{score_id}/grade/` - 성적 채점 (교사)

## 문서

- [Database Normalization](./docs/database-normalization.md)
- [Phase 3 Testing Plan](./docs/phase3-testing-plan.md)
- [Phase 4 API Test Results](./docs/phase4-api-test-results.md)
- [Coverage Improvement Report](./docs/coverage-improvement-report.md)
