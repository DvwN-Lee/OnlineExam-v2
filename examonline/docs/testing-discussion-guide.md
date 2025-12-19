# Testing Discussion Guide for Gemini

## 현재 상황

### 구현 완료 사항
- Phase 3 Question Management API 구현 완료
- 총 732줄의 코드 (Serializers, Filters, ViewSet, Tests)
- 8개 API Endpoints 생성
- 20개 pytest 테스트 케이스 작성
- OpenAPI Schema 생성 성공

### 구현된 파일
```
apps/testquestion/api/
├── __init__.py         (3줄)
├── serializers.py      (211줄) - 7개 Serializer 클래스
├── filters.py          (52줄)  - QuestionFilter
├── views.py            (189줄) - QuestionViewSet
├── urls.py             (15줄)  - URL 라우팅
└── tests.py            (262줄) - 20개 테스트 케이스
```

### 현재 이슈
**Database Connection Error**
- Docker daemon 미실행 상태
- PostgreSQL 연결 불가: `psycopg.OperationalError`

---

## Gemini와 논의할 테스트 전략

### 1. 테스트 환경 설정

**Question 1: Docker 없이 테스트 가능한가?**
- SQLite로 전환하여 로컬 테스트 가능 여부
- In-memory database를 사용한 단위 테스트
- Mock을 활용한 통합 테스트

**Question 2: 최소 환경에서 pytest 실행**
```bash
# pytest 설치 필요
pip install pytest pytest-django

# 현재 작성된 테스트 실행
pytest apps/testquestion/api/tests.py -v
```

### 2. 테스트 우선순위

**Phase 1: 단위 테스트 (pytest)**
- Serializer validation 테스트
- Permission 로직 테스트
- Filter 동작 테스트
- 장점: Database 연결 없이 실행 가능 (fixture 활용)

**Phase 2: API 통합 테스트 (Swagger UI)**
- 실제 HTTP 요청/응답 검증
- JWT 인증 흐름 테스트
- End-to-end 시나리오 검증
- 요구사항: Docker + Django server 실행 필요

**Phase 3: 부하 테스트 (선택)**
- Locust 또는 Apache Bench
- 동시 사용자 처리 능력 검증

### 3. 테스트 자동화 전략

**Question 3: CI/CD Pipeline 구축**
- GitHub Actions를 통한 자동 테스트
- Docker Compose를 활용한 테스트 환경 구성
- Test coverage 측정

예시 `.github/workflows/test.yml`:
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: |
          uv run pytest apps/testquestion/api/tests.py -v
```

---

## 테스트 시나리오 우선순위

### Critical (P0) - 반드시 통과해야 함
1. **인증 및 권한**
   - 비인증 사용자 차단
   - 학생의 문제 생성 차단
   - 교사의 문제 CRUD 권한

2. **CRUD 기본 기능**
   - 문제 생성 (옵션 포함)
   - 문제 조회 (목록/상세)
   - 문제 수정
   - 문제 삭제 (Soft Delete)

3. **Validation**
   - 객관식 문제 옵션 개수 검증
   - 정답 옵션 존재 여부 검증

### High (P1) - 주요 기능
4. **필터링 및 검색**
   - 과목별, 유형별, 난이도별 필터
   - 제목 검색

5. **공유 기능**
   - 문제 공유 설정/해제
   - 학생의 공유 문제 조회

### Medium (P2) - 편의 기능
6. **문제 은행**
   - 내 문제 목록 (교사)
   - 공유 문제 목록

7. **Pagination**
   - 페이지 크기 조정
   - 다음/이전 페이지 이동

---

## Gemini에게 물어볼 질문

### 기술적 질문
1. **Database 없이 테스트하는 Best Practice는?**
   - pytest의 `django_db` fixture 활용 방법
   - In-memory SQLite 사용 시 주의사항
   - Transaction rollback을 통한 테스트 격리

2. **Nested Serializer 테스트 전략은?**
   - 문제 생성 시 옵션이 함께 생성되는지 확인
   - 문제 수정 시 옵션이 올바르게 업데이트되는지 검증
   - Transaction atomic 동작 확인

3. **Permission 테스트의 Edge Case는?**
   - 삭제된 사용자의 문제 접근
   - 동시 수정 충돌 처리
   - 권한 변경 시 기존 문제 접근 권한

### 프로세스 질문
4. **Test Coverage는 몇 %가 적절한가?**
   - 현재 작성된 20개 테스트로 충분한가?
   - 추가로 필요한 테스트 케이스는?

5. **Integration Test vs Unit Test 비율은?**
   - API 통합 테스트와 단위 테스트의 적절한 비율
   - 각 테스트 유형의 장단점

6. **Performance Benchmark는?**
   - API 응답 시간 목표 (예: 95th percentile < 500ms)
   - 동시 사용자 처리 목표
   - Database query 최적화 방법

---

## 다음 단계 제안

### Step 1: 환경 준비
```bash
# Docker 시작 (Mac의 경우 Docker Desktop 실행)
open -a Docker

# 또는 Docker daemon 수동 시작
sudo systemctl start docker  # Linux

# Database 준비 확인
docker compose -f docker-compose.dev.yml ps
```

### Step 2: pytest 환경 설정
```bash
# pytest 및 관련 패키지 설치
pip install pytest pytest-django pytest-cov

# 또는 pyproject.toml에 추가 후
uv sync
```

pyproject.toml 업데이트:
```toml
[project.optional-dependencies]
test = [
    "pytest>=7.4",
    "pytest-django>=4.5",
    "pytest-cov>=4.1",
]
```

### Step 3: 테스트 실행
```bash
# 전체 테스트
uv run pytest apps/testquestion/api/tests.py -v

# Coverage와 함께 실행
uv run pytest apps/testquestion/api/tests.py --cov=apps/testquestion --cov-report=html

# 특정 테스트만 실행
uv run pytest apps/testquestion/api/tests.py::TestQuestionCRUD -v
```

### Step 4: Swagger UI 테스트
```bash
# 서버 시작
uv run python manage.py runserver

# 브라우저에서 접속
open http://localhost:8000/api/docs/
```

---

## 참고 문서

- 상세 테스트 계획: `/docs/phase3-testing-plan.md`
- API 구현 계획: `~/.claude/plans/idempotent-chasing-flask.md`
- Database 정규화: `/docs/database-normalization.md`

---

## Gemini와 논의 시작 예시

```
안녕하세요! Django REST Framework로 Question Management API를 구현했습니다.

현재 상황:
- 8개 API endpoints 구현 완료
- 20개 pytest 테스트 케이스 작성
- Docker database 연결 이슈로 통합 테스트 대기 중

질문:
1. Docker 없이 pytest로 API 테스트를 진행하는 것이 가능한가요?
2. 작성된 20개 테스트로 충분한 coverage인지 검토 부탁드립니다.
3. CI/CD 파이프라인 구성 시 추천하는 테스트 전략이 있나요?

테스트 계획 문서: [첨부]
구현 코드: apps/testquestion/api/
```
