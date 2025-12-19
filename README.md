# OnlineExam v2 - 온라인 시험 관리 시스템

Django 5.2 + React 19 기반 현대적인 온라인 시험 관리 시스템

## 프로젝트 개요

기존 Django 2.1 온라인 시험 시스템을 최신 기술 스택으로 완전히 재구성한 풀스택 + DevOps 프로젝트입니다.

### 기술 스택

**Backend:**
- Django 5.2 LTS
- Python 3.14
- Django REST Framework 3.16
- SimpleJWT (JWT 인증)
- PostgreSQL 18
- MongoDB 8 (로그 및 분석)
- Redis 8 (캐시 및 Celery)
- Celery 5.5 (비동기 작업)

**Frontend:**
- React 19
- TypeScript 6
- Vite 6
- Tailwind CSS
- shadcn/ui

**DevOps:**
- Docker & Docker Compose
- Kubernetes + Helm
- Terraform (IaC)
- ArgoCD (GitOps)
- GitHub Actions (CI/CD)
- Prometheus + Grafana + Loki (모니터링)

### 프로젝트 구조

```
OnlineExam-v2/
├── examonline/          # Django Backend
│   ├── apps/            # Django 앱
│   │   ├── user/        # 사용자 관리
│   │   ├── testquestion/# 문제 관리
│   │   ├── testpaper/   # 시험지 관리
│   │   ├── examination/ # 시험 관리
│   │   └── operation/   # 운영 (댓글, 메시지)
│   ├── core/            # 공통 유틸리티
│   │   └── api/         # 공통 API 컴포넌트
│   ├── config/          # 설정
│   │   ├── base.py      # 공통 설정
│   │   ├── local.py     # 개발 환경 설정
│   │   ├── production.py# 운영 환경 설정
│   │   └── api.py       # DRF 설정
│   └── docs/            # 문서
├── ui-mockups/          # Frontend UI 목업
└── frontend/            # React Frontend (예정)
```

## 개발 환경 설정

### 사전 요구사항

- Python 3.14+
- uv (Python package manager)
- PostgreSQL 18
- MongoDB 8
- Redis 8
- Docker & Docker Compose

### 설치 방법

1. Repository clone:
```bash
git clone https://github.com/yourusername/OnlineExam-v2.git
cd OnlineExam-v2/examonline
```

2. 의존성 설치:
```bash
uv sync
```

3. Database 서비스 시작:
```bash
docker compose -f docker-compose.dev.yml up -d
```

4. Migration 실행:
```bash
uv run python manage.py migrate
```

5. 개발 서버 시작:
```bash
uv run python manage.py runserver
```

6. API 문서 접근:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

## API Endpoint

### 인증
- `POST /api/v1/auth/register/` - 회원가입
- `POST /api/v1/auth/token/` - JWT Token 발급
- `POST /api/v1/auth/token/refresh/` - Token 갱신

### 사용자
- `GET /api/v1/users/me/` - 내 정보 조회
- `PATCH /api/v1/users/me/` - 프로필 수정
- `PUT /api/v1/users/me/change-password/` - 비밀번호 변경

### 과목
- `GET /api/v1/subjects/` - 과목 목록
- `POST /api/v1/subjects/` - 과목 생성 (교사 전용)

## 기능

### Phase 1: Infrastructure (완료)
- Django 5.2 LTS 업그레이드
- PostgreSQL 18 + MongoDB 8 + Redis 8
- Docker Compose 설정
- Database 정규화

### Phase 2: Core Backend API (완료)
- Django REST Framework
- JWT 인증
- 역할 기반 권한 (학생/교사)
- Swagger/OpenAPI 문서화
- 사용자 관리 API

### Phase 3: Question Management API (완료)
- Question CRUD (Issues #1)
- 필터링 및 검색 (Issues #2)
- 문제 공유 기능 (Issues #3)
- 문제 은행 관리 (Issues #4)
- Test Coverage: 98%

### Phase 4: Examination System API (완료)
- TestPaper Management (Issues #5)
- Examination Scheduling (Issues #6)
- Exam Taking (Issues #7)
- Scores & Grading (Issues #8)
- Test Coverage: 92-97%

### Phase 5: Frontend Development (계획)
- React 19 + TypeScript 프로젝트 초기화 (Issues #9)
- 인증 및 사용자 관리 UI (Issues #10)
- 문제 관리 UI (Issues #11)
- 시험지 및 시험 관리 UI (Issues #12)
- 시험 응시 UI (Issues #13)
- 대시보드 UI (Issues #14)

### Phase 6: DevOps & Deployment (계획)
- Docker & Docker Compose (Issues #15)
- Kubernetes + Helm (Issues #16)
- Terraform IaC (Issues #17)
- CI/CD Pipeline (Issues #18)
- ArgoCD GitOps (Issues #19)
- 모니터링 및 로깅 (Issues #20)
- Celery 비동기 작업 (Issues #21)

## 문서

- [Database 정규화 문서](examonline/docs/database-normalization.md)
- [UI 목업](ui-mockups/README.md)

## 기여

포트폴리오 및 학습 프로젝트입니다. Issue 및 Pull Request를 환영합니다.

## 라이선스

MIT License
