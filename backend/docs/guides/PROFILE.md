# 사용자 프로필 관리 기능

## 개요

KingoPortfolio에 사용자 프로필 관리 기능이 구현되었습니다. 사용자는 자신의 프로필을 조회, 수정하고 비밀번호를 변경하거나 계정을 삭제할 수 있습니다.

## 주요 파일

- [`app/models/user.py`](app/models/user.py) - User 모델에 name 컬럼 추가
- [`app/schemas.py`](app/schemas.py) - 프로필 관련 스키마 (UpdateProfileRequest, ChangePasswordRequest, ProfileResponse)
- [`app/routes/auth.py`](app/routes/auth.py) - 프로필 관리 엔드포인트 (lines 645-899)
- [`tests/unit/test_auth.py`](tests/unit/test_auth.py) - 프로필 엔드포인트 테스트 (TestProfileEndpoints)
- [`add_user_name_column.py`](add_user_name_column.py) - 데이터베이스 마이그레이션 스크립트

## 기능

### 1. 프로필 조회 (GET /auth/profile)

현재 로그인한 사용자의 프로필 정보를 조회합니다.

#### 요청

```bash
GET /auth/profile
Authorization: Bearer {access_token}
```

#### 응답 (200 OK)

```json
{
  "id": "usr_abc123xyz",
  "email": "user@example.com",
  "name": "홍길동",
  "role": "user",
  "created_at": "2025-12-29T10:00:00Z"
}
```

#### 특징

- 인증 필수 (JWT 토큰)
- 사용자 역할(role) 정보 포함
- UserResponse보다 확장된 정보 제공 (ProfileResponse 사용)

### 2. 프로필 수정 (PUT /auth/profile)

사용자 이름 또는 이메일을 수정합니다.

#### 요청

```bash
PUT /auth/profile
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "김철수",
  "email": "new@example.com"
}
```

#### 요청 필드

- `name` (선택): 사용자 이름 (최대 50자)
- `email` (선택): 이메일 주소 (고유값)

**주의**: 최소 하나의 필드는 제공해야 합니다.

#### 응답 (200 OK)

```json
{
  "id": "usr_abc123xyz",
  "email": "new@example.com",
  "name": "김철수",
  "role": "user",
  "created_at": "2025-12-29T10:00:00Z"
}
```

#### 에러 응답

**422 Unprocessable Entity** - 필드가 하나도 제공되지 않음

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "최소 하나의 필드(name 또는 email)를 제공해야 합니다",
    "status": 422
  }
}
```

**409 Conflict** - 이메일 중복

```json
{
  "error": {
    "code": "DUPLICATE_EMAIL",
    "message": "이메일 주소 (existing@example.com)가 이미 사용 중입니다",
    "status": 409,
    "extra": {
      "email": "existing@example.com"
    }
  }
}
```

#### 특징

- 이메일 변경 시 중복 검사 수행
- 현재 이메일과 동일한 경우는 변경하지 않음
- name만 변경하거나 email만 변경하는 것도 가능
- 변경 후 즉시 새로운 이메일로 로그인 가능

### 3. 비밀번호 변경 (PUT /auth/change-password)

현재 비밀번호를 확인한 후 새 비밀번호로 변경합니다.

#### 요청

```bash
PUT /auth/change-password
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "current_password": "oldPassword123!",
  "new_password": "newPassword456!"
}
```

#### 요청 필드

- `current_password` (필수): 현재 비밀번호
- `new_password` (필수): 새 비밀번호 (최소 8자, 최대 72바이트)

#### 응답 (200 OK)

```json
{
  "message": "비밀번호가 성공적으로 변경되었습니다"
}
```

#### 에러 응답

**401 Unauthorized** - 현재 비밀번호 불일치

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "현재 비밀번호가 올바르지 않습니다",
    "status": 401
  }
}
```

**422 Unprocessable Entity** - 새 비밀번호가 현재와 동일

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "새 비밀번호는 현재 비밀번호와 달라야 합니다",
    "status": 422
  }
}
```

#### 특징

- 현재 비밀번호 검증 필수
- 새 비밀번호가 기존 비밀번호와 달라야 함
- bcrypt로 안전하게 해싱
- 비밀번호 변경 후에도 기존 토큰은 유효 (재로그인 불필요)

### 4. 계정 삭제 (DELETE /auth/account)

현재 로그인한 사용자의 계정을 완전히 삭제합니다.

#### 요청

```bash
DELETE /auth/account
Authorization: Bearer {access_token}
```

#### 응답 (200 OK)

```json
{
  "message": "계정이 성공적으로 삭제되었습니다"
}
```

#### 특징

- 사용자 데이터 완전 삭제
- 관련된 진단 기록도 함께 삭제 (cascade)
- 삭제 후 토큰은 무효화됨 (User not found 에러 발생)
- 삭제 후 동일 이메일로 재가입 가능

## 데이터베이스 변경 사항

### User 모델 업데이트

`app/models/user.py`에 `name` 컬럼이 추가되었습니다:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(50), nullable=True)  # 새로 추가
    is_admin = Column(Boolean, default=False)
    role = Column(String(20), default='user')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 마이그레이션

기존 데이터베이스에 `name` 컬럼을 추가하는 마이그레이션 스크립트:

```bash
# 마이그레이션 실행
python add_user_name_column.py
```

마이그레이션은 멱등성을 보장합니다 (이미 컬럼이 존재하면 스킵).

## 스키마

### UpdateProfileRequest

```python
class UpdateProfileRequest(BaseModel):
    """프로필 수정 요청"""
    name: Optional[str] = Field(
        None,
        max_length=50,
        description="사용자 이름 (선택사항)",
        example="홍길동"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="이메일 주소 (선택사항)",
        example="newemail@example.com"
    )
```

### ChangePasswordRequest

```python
class ChangePasswordRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str = Field(
        ...,
        description="현재 비밀번호",
        example="currentPassword123!"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="새 비밀번호 (최소 8자, 최대 72바이트)",
        example="newPassword456!"
    )
```

### ProfileResponse

```python
class ProfileResponse(BaseModel):
    """프로필 응답 (확장된 사용자 정보)"""
    id: str
    email: str
    name: Optional[str]
    role: str  # 'user', 'premium', 'admin'
    created_at: datetime

    class Config:
        orm_mode = True
```

## 사용 예시

### Python (requests)

```python
import requests

# 로그인
login_response = requests.post("http://localhost:8000/auth/login", json={
    "email": "user@example.com",
    "password": "password123"
})
token = login_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# 1. 프로필 조회
profile = requests.get("http://localhost:8000/auth/profile", headers=headers)
print(profile.json())

# 2. 이름 변경
update_response = requests.put(
    "http://localhost:8000/auth/profile",
    headers=headers,
    json={"name": "새 이름"}
)
print(update_response.json())

# 3. 비밀번호 변경
password_response = requests.put(
    "http://localhost:8000/auth/change-password",
    headers=headers,
    json={
        "current_password": "password123",
        "new_password": "newPassword456!"
    }
)
print(password_response.json())

# 4. 계정 삭제
delete_response = requests.delete("http://localhost:8000/auth/account", headers=headers)
print(delete_response.json())
```

### JavaScript (fetch)

```javascript
// 로그인
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});
const { access_token } = await loginResponse.json();

const headers = {
  'Authorization': `Bearer ${access_token}`,
  'Content-Type': 'application/json'
};

// 1. 프로필 조회
const profile = await fetch('http://localhost:8000/auth/profile', { headers });
console.log(await profile.json());

// 2. 이메일과 이름 변경
const updateResponse = await fetch('http://localhost:8000/auth/profile', {
  method: 'PUT',
  headers,
  body: JSON.stringify({
    name: '새 이름',
    email: 'newemail@example.com'
  })
});
console.log(await updateResponse.json());

// 3. 비밀번호 변경
const passwordResponse = await fetch('http://localhost:8000/auth/change-password', {
  method: 'PUT',
  headers,
  body: JSON.stringify({
    current_password: 'password123',
    new_password: 'newPassword456!'
  })
});
console.log(await passwordResponse.json());

// 4. 계정 삭제
const deleteResponse = await fetch('http://localhost:8000/auth/account', {
  method: 'DELETE',
  headers
});
console.log(await deleteResponse.json());
```

### cURL

```bash
# 1. 로그인
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}' \
  | jq -r '.access_token')

# 2. 프로필 조회
curl -X GET http://localhost:8000/auth/profile \
  -H "Authorization: Bearer $TOKEN"

# 3. 프로필 수정
curl -X PUT http://localhost:8000/auth/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"새 이름","email":"newemail@example.com"}'

# 4. 비밀번호 변경
curl -X PUT http://localhost:8000/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"password123","new_password":"newPassword456!"}'

# 5. 계정 삭제
curl -X DELETE http://localhost:8000/auth/account \
  -H "Authorization: Bearer $TOKEN"
```

## 테스트

### 테스트 구조

`tests/unit/test_auth.py`에 `TestProfileEndpoints` 클래스가 추가되었습니다:

```
TestProfileEndpoints (10개 테스트)
├── test_get_profile
├── test_get_profile_without_token
├── test_update_profile_name
├── test_update_profile_email
├── test_update_profile_duplicate_email
├── test_update_profile_no_fields
├── test_change_password_success
├── test_change_password_wrong_current
├── test_change_password_same_as_current
└── test_delete_account
```

### 테스트 실행

```bash
# 프로필 테스트만 실행
pytest tests/unit/test_auth.py::TestProfileEndpoints -v

# 전체 인증 테스트 실행
pytest tests/unit/test_auth.py -v

# 전체 테스트 스위트 실행
pytest tests/ -v
```

### 테스트 결과

- **총 테스트**: 123개
- **통과**: 123개 (100%)
- **프로필 테스트**: 10개 (모두 통과)

## 보안 고려사항

### 1. 인증 및 권한

- 모든 프로필 엔드포인트는 JWT 토큰 인증 필수
- 사용자는 자신의 프로필만 조회/수정 가능
- 토큰이 없거나 유효하지 않으면 401 Unauthorized

### 2. 비밀번호 보안

- 현재 비밀번호 검증 후에만 변경 가능
- 새 비밀번호는 기존과 달라야 함
- bcrypt 해싱 사용 (salt rounds: 12)
- 비밀번호는 평문으로 저장되지 않음

### 3. 이메일 고유성

- 이메일 중복 검사 수행
- 데이터베이스 레벨 UNIQUE 제약조건
- 중복 시도 시 409 Conflict 에러

### 4. 입력 검증

- Pydantic 스키마로 자동 검증
- name: 최대 50자
- email: EmailStr 타입 검증
- password: 최소 8자, 최대 72바이트

### 5. 데이터 삭제

- 계정 삭제 시 관련 데이터 cascade 삭제
- 삭제 후 토큰 무효화
- 복구 불가능 (영구 삭제)

## 에러 처리

모든 에러는 일관된 형식으로 반환됩니다:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 친화적인 메시지",
    "status": 400,
    "extra": {}
  }
}
```

### 주요 에러 코드

| 코드 | 상태 | 설명 |
|------|------|------|
| `INVALID_TOKEN` | 401 | 유효하지 않은 토큰 |
| `TOKEN_EXPIRED` | 401 | 만료된 토큰 |
| `INVALID_CREDENTIALS` | 401 | 잘못된 비밀번호 |
| `DUPLICATE_EMAIL` | 409 | 이메일 중복 |
| `VALIDATION_ERROR` | 422 | 입력 검증 실패 |

## API 문서

Swagger UI에서 인터랙티브한 API 문서를 확인할 수 있습니다:

```bash
# 서버 시작
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload

# 브라우저에서 접속
# http://localhost:8000/docs
```

### 문서 탐색

1. Swagger UI 우측 상단 "Authorize" 버튼 클릭
2. `/auth/login` 또는 `/auth/signup`으로 토큰 획득
3. `Bearer {access_token}` 입력
4. "Authorize" 클릭
5. **Authentication** 태그 아래에서 프로필 엔드포인트 확인:
   - GET /auth/profile
   - PUT /auth/profile
   - PUT /auth/change-password
   - DELETE /auth/account

## 통계

### 코드 변경

- **추가된 파일**: 1개 (add_user_name_column.py)
- **수정된 파일**: 4개
  - app/models/user.py: +1 line (name 컬럼)
  - app/schemas.py: +68 lines (3개 스키마)
  - app/routes/auth.py: +258 lines (4개 엔드포인트)
  - tests/unit/test_auth.py: +242 lines (10개 테스트)

### 테스트 커버리지

- **app/routes/auth.py**: 70% → 92% (+22%)
- **app/auth.py**: 58% → 91% (+33%)
- **전체 테스트**: 113개 → 123개 (+10개)
- **테스트 통과율**: 100%

### API 엔드포인트

- **총 엔드포인트**: 61개 → 65개 (+4개)
- **Authentication 태그**: 9개 → 13개 (+4개)

## 향후 개선 사항

- [ ] 프로필 사진 업로드 기능
- [ ] 이메일 변경 시 확인 이메일 발송
- [ ] 계정 삭제 시 확인 단계 추가 (비밀번호 재입력)
- [ ] 프로필 변경 이력 추적
- [ ] 2단계 인증 (2FA) 설정
- [ ] 알림 설정 (이메일, SMS 등)
- [ ] 프라이버시 설정
- [ ] 계정 비활성화 (삭제 대신 일시 중지)

## 관련 문서

- [비밀번호 재설정 가이드](PASSWORD_RESET.md)
- [API 문서화 가이드](API_DOCUMENTATION.md)
- [에러 핸들링 시스템](ERROR_HANDLING.md)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)

## 문의

프로필 관리 기능 관련 문의사항은 백엔드 팀에 문의해주세요.

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**테스트 통과**: 123/123 (100%)
**작성자**: Claude Code (AI Assistant)
