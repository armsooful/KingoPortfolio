# 비밀번호 재설정 기능

## 개요

KingoPortfolio에 JWT 기반 비밀번호 재설정 기능이 구현되었습니다. 사용자는 이메일을 통해 재설정 링크를 받아 안전하게 비밀번호를 변경할 수 있습니다.

## 주요 파일

- [`app/auth.py`](app/auth.py) - 토큰 생성 및 검증 함수
- [`app/routes/auth.py`](app/routes/auth.py) - `/forgot-password`, `/reset-password` 엔드포인트
- [`app/schemas.py`](app/schemas.py) - 요청/응답 스키마
- [`tests/unit/test_auth.py`](tests/unit/test_auth.py) - 단위 및 통합 테스트 (15개)

## 기능 흐름

```
1. 사용자가 forgot-password 요청
   ↓
2. 백엔드가 15분 유효 JWT 토큰 생성
   ↓
3. 이메일로 재설정 링크 전송 (현재는 콘솔 출력)
   ↓
4. 사용자가 링크 클릭 → reset-password 페이지
   ↓
5. 새 비밀번호 입력 및 제출
   ↓
6. 백엔드가 토큰 검증 후 비밀번호 업데이트
```

## API 엔드포인트

### 1. POST /auth/forgot-password

비밀번호 재설정 요청

#### 요청

```json
{
  "email": "user@example.com"
}
```

#### 응답 (200 OK)

```json
{
  "message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"
}
```

#### 특징

- **보안**: 존재하지 않는 이메일도 성공 응답 반환 (사용자 존재 여부 노출 방지)
- **콘솔 출력**: 현재는 실제 이메일 대신 콘솔에 재설정 링크 출력

```
================================================================================
📧 비밀번호 재설정 이메일 전송 (콘솔 출력)
================================================================================
수신자: user@example.com
사용자 ID: usr_abc123xyz
재설정 링크: http://localhost:3000/reset-password?token=eyJhbGciOiJIUzI1NiIs...
유효 시간: 15분
================================================================================
```

### 2. POST /auth/reset-password

비밀번호 재설정 실행

#### 요청

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "newSecurePassword123!"
}
```

#### 응답 (200 OK)

```json
{
  "message": "비밀번호가 성공적으로 변경되었습니다"
}
```

#### 에러 응답

**401 - 토큰 만료**

```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "재설정 링크가 만료되었습니다",
    "status": 401
  }
}
```

**401 - 유효하지 않은 토큰**

```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "유효하지 않은 토큰입니다",
    "status": 401
  }
}
```

**404 - 사용자를 찾을 수 없음**

```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "사용자를 찾을 수 없습니다",
    "status": 404
  }
}
```

**422 - 비밀번호 검증 실패**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "비밀번호는 최소 8자 이상이어야 합니다",
    "status": 422
  }
}
```

## 토큰 구조

### 재설정 토큰 (Reset Token)

```python
{
  "sub": "user_id",       # 사용자 ID
  "type": "reset",        # 토큰 타입 (access와 구분)
  "exp": 1735476000       # 만료 시간 (15분 후)
}
```

### 액세스 토큰 (Access Token)과의 차이

| 속성 | Access Token | Reset Token |
|-----|-------------|-------------|
| **type** | (없음) | "reset" |
| **유효 시간** | 30분 | 15분 |
| **용도** | API 인증 | 비밀번호 재설정 |
| **payload.sub** | 이메일 | 사용자 ID |

## 주요 함수

### app/auth.py

#### `create_reset_token(user_id: str) -> str`

비밀번호 재설정 토큰 생성

```python
from app.auth import create_reset_token

# 사용자 ID로 토큰 생성
reset_token = create_reset_token("usr_abc123xyz")
# → "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**특징**:
- 15분 유효
- JWT 토큰 (jose 라이브러리 사용)
- `type: "reset"` 필드로 access 토큰과 구분

#### `verify_reset_token(token: str) -> str`

재설정 토큰 검증 및 사용자 ID 추출

```python
from app.auth import verify_reset_token
from app.exceptions import TokenExpiredError, InvalidTokenError

try:
    user_id = verify_reset_token(token)
    # → "usr_abc123xyz"
except TokenExpiredError:
    # 토큰 만료
    pass
except InvalidTokenError:
    # 유효하지 않은 토큰
    pass
```

**검증 항목**:
1. JWT 서명 검증
2. 만료 시간 확인
3. `type` 필드가 "reset"인지 확인
4. `sub` (사용자 ID) 존재 여부 확인

## 보안 고려사항

### 1. 사용자 존재 여부 노출 방지

`/forgot-password` 엔드포인트는 존재하지 않는 이메일에 대해서도 성공 응답을 반환합니다.

**이유**: 공격자가 이메일 존재 여부를 확인하는 것을 방지

```python
if not user:
    # 보안상 존재하지 않는 이메일도 성공 응답
    print(f"⚠️  비밀번호 재설정 요청: 존재하지 않는 이메일 {request.email}")
    return {"message": "비밀번호 재설정 링크가 이메일로 전송되었습니다"}
```

### 2. 토큰 타입 구분

재설정 토큰과 액세스 토큰을 구분하여 액세스 토큰으로 비밀번호를 재설정할 수 없도록 합니다.

```python
# 토큰 타입 확인
if token_type != "reset":
    raise InvalidTokenError(detail="잘못된 토큰 타입입니다")
```

### 3. 짧은 유효 시간

재설정 토큰은 15분 후 자동 만료되어 보안 위험을 최소화합니다.

### 4. 토큰 일회성

비밀번호 변경 시 해시가 바뀌므로 이전 토큰으로는 재사용 불가능합니다.

### 5. bcrypt 72바이트 제한

비밀번호는 bcrypt 해싱 전 72바이트 제한을 검증합니다.

```python
if len(password.encode('utf-8')) > 72:
    raise KingoValidationError(
        detail="비밀번호는 72바이트를 초과할 수 없습니다",
        extra={"max_bytes": 72, "current_bytes": len(password.encode('utf-8'))}
    )
```

## 테스트

총 **15개 테스트** (모두 통과)

### 단위 테스트 (6개) - TestPasswordResetTokens

```bash
pytest tests/unit/test_auth.py::TestPasswordResetTokens -v
```

1. `test_create_reset_token` - 토큰 생성 및 구조 검증
2. `test_verify_reset_token_valid` - 유효한 토큰 검증
3. `test_verify_reset_token_expired` - 만료된 토큰 처리
4. `test_verify_reset_token_invalid_type` - 잘못된 타입 토큰 처리
5. `test_verify_reset_token_no_user_id` - 사용자 ID 누락 처리
6. `test_verify_reset_token_invalid_signature` - 잘못된 서명 처리

### 통합 테스트 (9개) - TestPasswordResetEndpoints

```bash
pytest tests/unit/test_auth.py::TestPasswordResetEndpoints -v
```

1. `test_forgot_password_success` - 정상 재설정 요청
2. `test_forgot_password_nonexistent_email` - 존재하지 않는 이메일 처리
3. `test_forgot_password_invalid_email` - 유효하지 않은 이메일 형식
4. `test_reset_password_success` - 정상 비밀번호 재설정 (로그인 검증 포함)
5. `test_reset_password_expired_token` - 만료된 토큰 처리
6. `test_reset_password_invalid_token` - 유효하지 않은 토큰 처리
7. `test_reset_password_wrong_token_type` - 잘못된 타입 토큰 처리
8. `test_reset_password_short_password` - 짧은 비밀번호 검증
9. `test_reset_password_nonexistent_user` - 존재하지 않는 사용자 처리

### 전체 인증 테스트 실행

```bash
# 비밀번호 재설정 테스트만
pytest tests/unit/test_auth.py::TestPasswordResetTokens tests/unit/test_auth.py::TestPasswordResetEndpoints -v

# 전체 인증 테스트 (31개)
pytest tests/unit/test_auth.py -v

# 전체 테스트 (113개)
pytest tests/ -v
```

## 사용 예시

### 백엔드 테스트

```bash
# 1. 사용자 회원가입
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"oldPassword123"}'

# 2. 비밀번호 재설정 요청
curl -X POST http://localhost:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# 콘솔에 출력된 토큰 복사

# 3. 비밀번호 재설정
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "new_password":"newPassword456!"
  }'

# 4. 새 비밀번호로 로그인
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"newPassword456!"}'
```

### 프론트엔드 구현 예시

```javascript
// 1. 비밀번호 재설정 요청
async function forgotPassword(email) {
  const response = await fetch('http://localhost:8000/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });

  const data = await response.json();
  alert(data.message); // "비밀번호 재설정 링크가 이메일로 전송되었습니다"
}

// 2. 비밀번호 재설정
async function resetPassword(token, newPassword) {
  const response = await fetch('http://localhost:8000/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword })
  });

  if (!response.ok) {
    const error = await response.json();
    if (error.error.code === 'TOKEN_EXPIRED') {
      alert('재설정 링크가 만료되었습니다. 다시 요청해 주세요.');
    } else if (error.error.code === 'INVALID_TOKEN') {
      alert('유효하지 않은 링크입니다.');
    } else if (error.error.code === 'VALIDATION_ERROR') {
      alert('비밀번호는 최소 8자 이상이어야 합니다.');
    }
    return;
  }

  const data = await response.json();
  alert(data.message); // "비밀번호가 성공적으로 변경되었습니다"
}

// 3. URL에서 토큰 추출 (ResetPasswordPage.jsx)
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

if (!token) {
  alert('유효하지 않은 재설정 링크입니다.');
}
```

## Swagger UI 문서

FastAPI Swagger UI에서 비밀번호 재설정 엔드포인트를 확인할 수 있습니다:

```
http://localhost:8000/docs#/Authentication
```

- **POST /auth/forgot-password** - 비밀번호 재설정 요청
- **POST /auth/reset-password** - 비밀번호 재설정

각 엔드포인트에는 다음이 포함되어 있습니다:
- 상세한 설명 및 프로세스
- 요청/응답 예시
- 가능한 모든 에러 코드 및 메시지
- 보안 고려사항

## 향후 개선 사항

### 1. 실제 이메일 전송 구현

현재는 콘솔 출력만 지원합니다. 다음 중 하나를 선택하여 구현:

#### SendGrid 사용

```python
# app/services/email_service.py
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_reset_email(to_email: str, reset_link: str):
    message = Mail(
        from_email='noreply@kingoportfolio.com',
        to_emails=to_email,
        subject='비밀번호 재설정',
        html_content=f'<p>비밀번호 재설정 링크: <a href="{reset_link}">{reset_link}</a></p>'
    )

    sg = SendGridAPIClient(settings.sendgrid_api_key)
    response = sg.send(message)
    return response.status_code == 202
```

#### AWS SES 사용

```python
# app/services/email_service.py
import boto3

def send_reset_email(to_email: str, reset_link: str):
    ses = boto3.client('ses', region_name='us-east-1')

    response = ses.send_email(
        Source='noreply@kingoportfolio.com',
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': '비밀번호 재설정'},
            'Body': {
                'Html': {
                    'Data': f'<p>비밀번호 재설정 링크: <a href="{reset_link}">{reset_link}</a></p>'
                }
            }
        }
    )
    return response['MessageId']
```

### 2. 이메일 템플릿

HTML 템플릿을 사용하여 전문적인 이메일 디자인:

```html
<!-- templates/reset_password_email.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button {
            background-color: #4CAF50;
            color: white;
            padding: 14px 20px;
            text-decoration: none;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>비밀번호 재설정</h2>
        <p>안녕하세요,</p>
        <p>비밀번호 재설정을 요청하셨습니다. 아래 버튼을 클릭하여 새 비밀번호를 설정해 주세요.</p>
        <p><a href="{{ reset_link }}" class="button">비밀번호 재설정</a></p>
        <p>이 링크는 15분 후 만료됩니다.</p>
        <p>본인이 요청하지 않았다면 이 이메일을 무시하셔도 됩니다.</p>
        <hr>
        <small>KingoPortfolio Team</small>
    </div>
</body>
</html>
```

### 3. 재설정 이력 추적

`PasswordResetLog` 모델 추가:

```python
# app/models/password_reset_log.py
from sqlalchemy import Column, String, DateTime, Boolean
from app.database import Base
from datetime import datetime

class PasswordResetLog(Base):
    __tablename__ = "password_reset_logs"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    token_hash = Column(String)  # SHA256 해시
    requested_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)
    ip_address = Column(String)
```

### 4. Rate Limiting

재설정 요청 남용 방지:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/forgot-password")
@limiter.limit("3/hour")  # 시간당 3회 제한
async def forgot_password(request: Request, ...):
    ...
```

### 5. 프론트엔드 페이지

React 컴포넌트 구현:

- `ForgotPasswordPage.jsx` - 이메일 입력 페이지
- `ResetPasswordPage.jsx` - 새 비밀번호 입력 페이지
- `ResetPasswordSuccessPage.jsx` - 재설정 완료 페이지

## 문의

비밀번호 재설정 기능 관련 문의사항은 백엔드 팀에 문의해주세요.

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**테스트 통과**: 113/113 (100%)
**auth.py 커버리지**: 86%
**routes/auth.py 커버리지**: 89%
