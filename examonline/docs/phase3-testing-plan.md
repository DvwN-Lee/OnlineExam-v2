# Phase 3: Question Management API Testing Plan

## 개요

Question Management API의 기능 및 통합 테스트 계획.

---

## 1. API Endpoints

| Method | Endpoint | 기능 | 권한 |
|--------|----------|------|------|
| GET | `/api/v1/questions/` | 문제 목록 조회 | Authenticated |
| POST | `/api/v1/questions/` | 문제 생성 | Teacher |
| GET | `/api/v1/questions/{id}/` | 문제 상세 조회 | Authenticated |
| PUT | `/api/v1/questions/{id}/` | 문제 전체 수정 | Creator |
| PATCH | `/api/v1/questions/{id}/` | 문제 부분 수정 | Creator |
| DELETE | `/api/v1/questions/{id}/` | 문제 삭제 (Soft) | Creator |
| POST | `/api/v1/questions/{id}/share/` | 공유 상태 변경 | Creator |
| GET | `/api/v1/questions/my/` | 내 문제 목록 | Teacher |
| GET | `/api/v1/questions/shared/` | 공유 문제 목록 | Authenticated |

---

## 2. Test Scenarios

### 2.1 인증 및 권한 테스트

**Scenario 1: 비인증 사용자 접근**
```
- 요청: GET /api/v1/questions/
- 인증: None
- 예상 결과: 401 Unauthorized
```

**Scenario 2: 학생의 문제 생성 시도**
```
- 요청: POST /api/v1/questions/
- 인증: Student token
- 예상 결과: 403 Forbidden
```

**Scenario 3: 교사의 문제 생성**
```
- 요청: POST /api/v1/questions/
- 인증: Teacher token
- Body: {
    "name": "Test Question",
    "subject_id": 1,
    "score": 10,
    "tq_type": "xz",
    "tq_degree": "jd",
    "options": [
        {"option": "Answer A", "is_right": true},
        {"option": "Answer B", "is_right": false}
    ]
  }
- 예상 결과: 201 Created
```

### 2.2 CRUD 기능 테스트

**Scenario 4: 문제 목록 조회 (교사)**
```
- 요청: GET /api/v1/questions/
- 인증: Teacher token
- 예상 결과:
  - 본인이 생성한 문제 + 공유된 문제 반환
  - Pagination 적용
```

**Scenario 5: 문제 목록 조회 (학생)**
```
- 요청: GET /api/v1/questions/
- 인증: Student token
- 예상 결과:
  - 공유된 문제만 반환 (is_share=True, is_del=False)
```

**Scenario 6: 문제 상세 조회**
```
- 요청: GET /api/v1/questions/{id}/
- 인증: Teacher/Student token
- 예상 결과:
  - 문제 정보 + 옵션 목록 포함
  - 학생은 공유되지 않은 문제 조회 불가 (403)
```

**Scenario 7: 문제 수정**
```
- 요청: PATCH /api/v1/questions/{id}/
- 인증: Creator token
- Body: {"name": "Updated Question"}
- 예상 결과: 200 OK, 문제명 업데이트
```

**Scenario 8: 옵션 포함 문제 수정**
```
- 요청: PATCH /api/v1/questions/{id}/
- 인증: Creator token
- Body: {
    "options": [
        {"id": 1, "option": "Updated A", "is_right": true},
        {"option": "New Option C", "is_right": false}
    ]
  }
- 예상 결과:
  - 기존 옵션 (id=1) 수정
  - 새 옵션 생성
  - 요청에 없는 기존 옵션은 삭제
```

**Scenario 9: 문제 삭제 (Soft Delete)**
```
- 요청: DELETE /api/v1/questions/{id}/
- 인증: Creator token
- 예상 결과:
  - 204 No Content
  - is_del=True 설정
  - 목록 조회 시 나타나지 않음
```

### 2.3 필터링 및 검색 테스트

**Scenario 10: 과목별 필터링**
```
- 요청: GET /api/v1/questions/?subject=1
- 예상 결과: subject_id=1인 문제만 반환
```

**Scenario 11: 문제 유형 필터링**
```
- 요청: GET /api/v1/questions/?tq_type=xz
- 예상 결과: 객관식 문제만 반환
```

**Scenario 12: 난이도 필터링**
```
- 요청: GET /api/v1/questions/?tq_degree=jd
- 예상 결과: 쉬운 문제만 반환
```

**Scenario 13: 점수 범위 필터링**
```
- 요청: GET /api/v1/questions/?score_min=5&score_max=15
- 예상 결과: 5점~15점 사이 문제만 반환
```

**Scenario 14: 제목 검색**
```
- 요청: GET /api/v1/questions/?search=Python
- 예상 결과: 제목에 "Python" 포함된 문제 반환
```

**Scenario 15: 복합 필터**
```
- 요청: GET /api/v1/questions/?subject=1&tq_type=xz&tq_degree=zd&search=Test
- 예상 결과: 모든 조건을 만족하는 문제 반환
```

**Scenario 16: 정렬**
```
- 요청: GET /api/v1/questions/?ordering=-score
- 예상 결과: 점수 내림차순 정렬
```

### 2.4 공유 기능 테스트

**Scenario 17: 문제 공유 설정**
```
- 요청: POST /api/v1/questions/{id}/share/
- 인증: Creator token
- Body: {"is_share": true}
- 예상 결과:
  - 200 OK
  - is_share=True 설정
  - 학생이 해당 문제 조회 가능
```

**Scenario 18: 공유 해제**
```
- 요청: POST /api/v1/questions/{id}/share/
- 인증: Creator token
- Body: {"is_share": false}
- 예상 결과:
  - 200 OK
  - is_share=False 설정
  - 학생이 해당 문제 조회 불가
```

**Scenario 19: 다른 사용자의 문제 공유 시도**
```
- 요청: POST /api/v1/questions/{id}/share/
- 인증: 다른 Teacher token
- 예상 결과: 403 Forbidden
```

### 2.5 문제 은행 기능 테스트

**Scenario 20: 내 문제 목록 (교사)**
```
- 요청: GET /api/v1/questions/my/
- 인증: Teacher token
- 예상 결과:
  - 해당 교사가 생성한 문제만 반환
  - 필터링/검색/정렬 적용 가능
```

**Scenario 21: 내 문제 목록 (학생)**
```
- 요청: GET /api/v1/questions/my/
- 인증: Student token
- 예상 결과: 403 Forbidden
```

**Scenario 22: 공유 문제 목록**
```
- 요청: GET /api/v1/questions/shared/
- 인증: Teacher/Student token
- 예상 결과:
  - is_share=True, is_del=False인 모든 문제 반환
  - 필터링/검색/정렬 적용 가능
```

### 2.6 Validation 테스트

**Scenario 23: 객관식 문제 - 옵션 부족**
```
- 요청: POST /api/v1/questions/
- Body: {
    "tq_type": "xz",
    "options": [{"option": "Only one", "is_right": true}]
  }
- 예상 결과: 400 Bad Request
- 에러 메시지: "객관식 문제는 최소 2개 이상의 옵션이 필요합니다."
```

**Scenario 24: 객관식 문제 - 정답 없음**
```
- 요청: POST /api/v1/questions/
- Body: {
    "tq_type": "xz",
    "options": [
        {"option": "A", "is_right": false},
        {"option": "B", "is_right": false}
    ]
  }
- 예상 결과: 400 Bad Request
- 에러 메시지: "최소 1개 이상의 정답 옵션이 필요합니다."
```

**Scenario 25: 주관식/빈칸채우기 문제 - 옵션 없음**
```
- 요청: POST /api/v1/questions/
- Body: {
    "tq_type": "pd",  // 또는 "tk"
    "options": []
  }
- 예상 결과: 201 Created (옵션 없이 생성 가능)
```

---

## 3. 테스트 데이터 준비

### 3.1 사용자 생성
```bash
# Superuser 생성 (관리자 페이지 접속용)
uv run python manage.py createsuperuser

# 또는 Django shell에서 테스트 사용자 생성
uv run python manage.py shell
```

```python
from user.models import UserProfile, SubjectInfo

# 교사 사용자 생성
teacher = UserProfile.objects.create_user(
    username='teacher1',
    email='teacher@example.com',
    password='teacher123',
    user_type='teacher',
    nick_name='Teacher Kim'
)

# 학생 사용자 생성
student = UserProfile.objects.create_user(
    username='student1',
    email='student@example.com',
    password='student123',
    user_type='student',
    nick_name='Student Lee'
)

# 과목 생성
math = SubjectInfo.objects.create(subject_name='Mathematics')
science = SubjectInfo.objects.create(subject_name='Science')
```

### 3.2 JWT Token 발급
```bash
# cURL 사용
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teacher1", "password": "teacher123"}'

# HTTPie 사용
http POST http://localhost:8000/api/v1/auth/token/ \
  username=teacher1 password=teacher123
```

---

## 4. 테스트 실행 방법

### 4.1 Swagger UI (추천)
```
1. 서버 실행: uv run python manage.py runserver
2. 브라우저에서 http://localhost:8000/api/docs/ 접속
3. "Authorize" 버튼 클릭
4. Token 입력: Bearer {access_token}
5. 각 endpoint 테스트 실행
```

### 4.2 cURL
```bash
# 문제 목록 조회
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/v1/questions/

# 문제 생성
curl -X POST http://localhost:8000/api/v1/questions/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Question",
    "subject_id": 1,
    "score": 10,
    "tq_type": "xz",
    "tq_degree": "jd",
    "options": [
      {"option": "A", "is_right": true},
      {"option": "B", "is_right": false}
    ]
  }'
```

### 4.3 HTTPie
```bash
# 문제 목록 조회
http GET http://localhost:8000/api/v1/questions/ \
  "Authorization: Bearer {token}"

# 문제 생성
http POST http://localhost:8000/api/v1/questions/ \
  "Authorization: Bearer {token}" \
  name="Test Question" \
  subject_id:=1 \
  score:=10 \
  tq_type=xz \
  tq_degree=jd \
  options:='[{"option":"A","is_right":true},{"option":"B","is_right":false}]'
```

### 4.4 pytest (단위 테스트)
```bash
# 전체 테스트 실행
pytest apps/testquestion/api/tests.py -v

# 특정 테스트 클래스 실행
pytest apps/testquestion/api/tests.py::TestQuestionCRUD -v

# 특정 테스트 실행
pytest apps/testquestion/api/tests.py::TestQuestionCRUD::test_create_question_as_teacher -v
```

---

## 5. 성능 테스트

### 5.1 부하 테스트 (Locust)
```python
# locustfile.py
from locust import HttpUser, task, between

class QuestionAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/token/", json={
            "username": "teacher1",
            "password": "teacher123"
        })
        self.token = response.json()["access"]

    @task(3)
    def list_questions(self):
        self.client.get("/api/v1/questions/", headers={
            "Authorization": f"Bearer {self.token}"
        })

    @task(1)
    def create_question(self):
        self.client.post("/api/v1/questions/", json={
            "name": "Load Test Question",
            "subject_id": 1,
            "score": 10,
            "tq_type": "xz",
            "tq_degree": "jd",
            "options": [
                {"option": "A", "is_right": True},
                {"option": "B", "is_right": False}
            ]
        }, headers={
            "Authorization": f"Bearer {self.token}"
        })
```

실행:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## 6. 예상 문제 및 해결 방안

### Issue 1: Database Connection Error
**증상**: `psycopg.OperationalError: connection failed`
**해결**:
```bash
# Docker 서비스 상태 확인
docker compose -f docker-compose.dev.yml ps

# 필요시 재시작
docker compose -f docker-compose.dev.yml restart postgres
```

### Issue 2: JWT Token Expired
**증상**: `401 Unauthorized` with "Token is invalid or expired"
**해결**: Refresh token으로 새 access token 발급
```bash
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "{refresh_token}"}'
```

### Issue 3: CORS Error (Frontend 연동 시)
**증상**: Browser console에서 CORS 에러
**해결**: `config/api.py`의 `CORS_ALLOWED_ORIGINS` 확인

---

## 7. Checklist

### 기능 테스트
- [ ] 인증 및 권한 (Scenario 1-3)
- [ ] CRUD 기본 기능 (Scenario 4-9)
- [ ] 필터링 및 검색 (Scenario 10-16)
- [ ] 공유 기능 (Scenario 17-19)
- [ ] 문제 은행 (Scenario 20-22)
- [ ] Validation (Scenario 23-25)

### 비기능 테스트
- [ ] API 응답 시간 (< 500ms)
- [ ] Pagination 동작 확인
- [ ] 동시 접속 처리
- [ ] 에러 메시지 명확성

### 문서 검증
- [ ] Swagger UI에서 모든 endpoint 표시
- [ ] 각 endpoint의 설명 및 예시 확인
- [ ] Request/Response schema 정확성
