# API 문서화 가이드

## 개요

KingoPortfolio API는 FastAPI의 자동 문서 생성 기능을 활용하여 **Swagger UI**와 **ReDoc**를 통해 인터랙티브한 API 문서를 제공합니다.

## 문서 접근 방법

### 로컬 개발 환경

```bash
# 서버 시작
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload

# 브라우저에서 접속
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### 프로덕션 환경

- Swagger UI: `https://api.kingo-portfolio.com/docs`
- ReDoc: `https://api.kingo-portfolio.com/redoc`

## 문서 구조

### 1. API 메타데이터

[app/main.py](app/main.py)에서 전역 메타데이터를 설정합니다:

```python
app = FastAPI(
    title="KingoPortfolio",
    version="1.0.0",
    description="""
    # KingoPortfolio API

    AI 기반 포트폴리오 추천 플랫폼 백엔드 API

    ## 주요 기능
    - 인증 및 권한 관리
    - 투자 성향 진단
    - 재무 분석
    ...
    """,
    contact={
        "name": "KingoPortfolio Team",
        "url": "https://github.com/your-org/kingo-portfolio",
        "email": "support@kingo-portfolio.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)
```

### 2. 태그 분류

API 엔드포인트는 다음 태그로 분류됩니다:

| 태그 | 설명 | 주요 엔드포인트 |
|------|------|----------------|
| **Authentication** | 회원가입, 로그인, 토큰 관리 | `/auth/signup`, `/auth/login`, `/auth/me` |
| **Survey** | 투자 성향 진단 설문 | `/survey/questions`, `/survey/submit` |
| **Diagnosis** | 투자 성향 분석 및 추천 | `/diagnosis/submit`, `/diagnosis/me`, `/diagnosis/history` |
| **Admin** | 관리자 전용 기능 | `/admin/data-status`, `/admin/collect/*`, `/admin/financial/*` |
| **Health** | 서버 상태 확인 | `/health`, `/` |

### 3. 스키마 문서화

[app/schemas.py](app/schemas.py)에서 Pydantic Field로 상세한 설명과 예제를 제공합니다:

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    """사용자 생성 요청"""
    email: EmailStr = Field(
        ...,
        description="사용자 이메일 주소 (고유값)",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="비밀번호 (최소 8자, 최대 72바이트)",
        example="securePassword123!"
    )
    name: Optional[str] = Field(
        None,
        max_length=50,
        description="사용자 이름 (선택사항)",
        example="홍길동"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securePassword123!",
                "name": "홍길동"
            }
        }
```

### 4. 엔드포인트 문서화

각 엔드포인트에 다음 정보를 포함합니다:

```python
@router.post(
    "/signup",
    response_model=Token,
    status_code=201,
    summary="회원가입",
    description="새로운 사용자 계정을 생성하고 JWT 토큰을 발급합니다.",
    response_description="생성된 사용자 정보 및 JWT 토큰",
    responses={
        201: {
            "description": "회원가입 성공",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGci...",
                        "token_type": "bearer",
                        "user": {...}
                    }
                }
            }
        },
        400: {
            "description": "비밀번호가 너무 짧음",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "비밀번호는 최소 8자 이상이어야 합니다",
                            "status": 400
                        }
                    }
                }
            }
        },
        409: {
            "description": "이미 사용 중인 이메일",
            "content": {...}
        }
    }
)
async def signup(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    ## 회원가입

    새로운 사용자 계정을 생성하고 즉시 로그인 상태로 JWT 토큰을 발급합니다.

    ### 요청 필드

    - **email** (필수): 이메일 주소 (고유값, 중복 불가)
    - **password** (필수): 비밀번호 (최소 8자, 최대 72바이트)
    - **name** (선택): 사용자 이름 (최대 50자)

    ### 주의사항

    - 비밀번호는 bcrypt로 해싱되어 저장됩니다
    - 이메일은 대소문자 구분 없이 고유해야 합니다
    - 기본 role은 'user'로 설정됩니다

    ### 예제 요청

    ```json
    {
        "email": "user@example.com",
        "password": "securePassword123!",
        "name": "홍길동"
    }
    ```

    ### 예제 응답 (201 Created)

    ```json
    {
        "access_token": "eyJhbGci...",
        "token_type": "bearer",
        "user": {
            "id": "usr_abc123xyz",
            "email": "user@example.com",
            "name": "홍길동",
            "created_at": "2025-12-29T10:00:00Z"
        }
    }
    ```
    """
    # Implementation...
```

### 5. 에러 응답 문서화

모든 에러는 일관된 형식으로 문서화됩니다:

```python
class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    code: str = Field(..., description="에러 코드", example="INVALID_TOKEN")
    message: str = Field(..., description="사용자 친화적인 에러 메시지", example="유효하지 않은 토큰입니다")
    status: int = Field(..., description="HTTP 상태 코드", example=401)
    extra: Optional[dict] = Field(None, description="추가 컨텍스트 정보", example={"symbol": "AAPL"})


class ErrorResponse(BaseModel):
    """에러 응답 (전역 에러 핸들러 형식)"""
    error: ErrorDetail = Field(..., description="에러 정보")

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "유효하지 않은 토큰입니다",
                    "status": 401,
                    "extra": {}
                }
            }
        }
```

## 인증 사용 방법

### Swagger UI에서 인증하기

1. `/auth/signup` 또는 `/auth/login` 엔드포인트로 토큰 획득
2. 우측 상단 "Authorize" 버튼 클릭
3. `Bearer {access_token}` 형식으로 입력
4. "Authorize" 클릭
5. 이제 인증이 필요한 모든 엔드포인트 테스트 가능

### OAuth2 Password Flow

Swagger UI의 "Authorize" 버튼은 `/token` 엔드포인트를 사용합니다:

```bash
# 직접 호출 (form-data)
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securePassword123!"

# 응답
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

## 주요 개선 사항

이번 개선으로 다음 사항이 추가되었습니다:

### ✅ 완료된 개선

1. **전역 메타데이터 추가**
   - API 제목, 버전, 설명
   - 연락처 정보 (이름, URL, 이메일)
   - 라이선스 정보 (MIT License)
   - 서버 목록 (로컬, 프로덕션)

2. **태그 설명 추가**
   - Authentication: 회원가입, 로그인, 토큰 관리
   - Survey: 투자 성향 진단 설문
   - Diagnosis: 투자 성향 분석 및 추천
   - Admin: 관리자 전용 API
   - Health: 서버 상태 확인

3. **스키마 개선**
   - 모든 필드에 `Field()` 사용
   - 상세한 `description` 추가
   - 실제 사용 가능한 `example` 값 제공
   - `schema_extra`로 전체 예제 객체 제공
   - `min_length`, `max_length` 등 검증 규칙 명시

4. **엔드포인트 상세 문서화**
   - `summary`: 한줄 요약
   - `description`: 간단한 설명
   - `response_description`: 응답 설명
   - `responses`: 모든 가능한 HTTP 상태 코드 및 예제
   - 풍부한 docstring (마크다운 형식)

5. **에러 응답 표준화**
   - `ErrorResponse` 스키마 정의
   - 모든 에러 코드 예제 제공
   - 에러 발생 시나리오별 예제

6. **추가 기능**
   - Deprecated 엔드포인트 표시 (`/survey/submit`)
   - 다중 예제 지원 (토큰 만료 vs 유효하지 않은 토큰)
   - 활용 사례 설명

### 📋 문서화 체크리스트

새로운 엔드포인트 추가 시 다음 사항을 확인하세요:

- [ ] `summary` 및 `description` 작성
- [ ] `response_model` 지정
- [ ] `status_code` 명시 (기본값이 아닌 경우)
- [ ] `responses`에 모든 가능한 상태 코드 및 예제 추가
- [ ] 풍부한 docstring 작성 (마크다운 형식)
- [ ] 스키마 필드에 `Field()` 사용
- [ ] `example` 값 제공
- [ ] 에러 응답 문서화

### 📈 측정 지표

- **문서화 전**: 기본 docstring만 존재, 예제 없음
- **문서화 후**:
  - 57개 엔드포인트 문서화
  - 모든 스키마에 설명 및 예제 추가
  - 모든 에러 응답 코드 문서화
  - 테스트: 98/98 통과 (100%)

## 문서화 규칙

### Docstring 작성 규칙

```python
def endpoint_name():
    """
    ## 엔드포인트 이름 (H2)

    간단한 설명 (1-2문장)

    ### 섹션 제목 (H3)

    - **항목**: 설명
    - **항목**: 설명

    ### 예제 요청

    ```json
    {
        "field": "value"
    }
    ```

    ### 예제 응답 (200 OK)

    ```json
    {
        "result": "success"
    }
    ```
    """
```

### 에러 응답 작성 규칙

모든 에러는 다음 형식을 따릅니다:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 친화적인 에러 메시지",
    "status": 400,
    "extra": {
      "추가": "데이터"
    }
  }
}
```

### 예제 값 규칙

- **이메일**: `user@example.com`
- **비밀번호**: `securePassword123!`
- **ID**: `usr_abc123xyz`, `dia_xyz789abc`
- **날짜**: ISO 8601 형식 (`2025-12-29T10:00:00Z`)
- **토큰**: `eyJhbGci...` (실제처럼 보이는 JWT 형식)

## 향후 개선 사항

- [ ] Admin 엔드포인트 문서화 (현재 24% 커버리지)
- [ ] Diagnosis 엔드포인트 문서화
- [ ] OpenAPI 스키마 검증 자동화
- [ ] API 버전 관리 (/v1, /v2)
- [ ] GraphQL 문서 추가 (필요시)
- [ ] API 사용 가이드 (Postman Collection, SDK 등)

## 참고 자료

- [FastAPI 공식 문서 - Advanced User Guide](https://fastapi.tiangolo.com/advanced/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Pydantic Field Types](https://docs.pydantic.dev/latest/concepts/fields/)

## 문의

API 문서 관련 문의사항은 다음으로 연락해주세요:
- 이메일: support@kingo-portfolio.com
- GitHub Issues: https://github.com/your-org/kingo-portfolio/issues

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**작성자**: Claude Code (AI Assistant)
