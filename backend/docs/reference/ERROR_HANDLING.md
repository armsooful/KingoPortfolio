# 전역 에러 핸들링 시스템

## 개요

KingoPortfolio에 일관된 에러 핸들링 시스템이 구현되었습니다. 모든 예외는 중앙집중식으로 처리되며, 클라이언트에게 일관된 형식의 에러 응답을 제공합니다.

## 주요 파일

- [`app/exceptions.py`](app/exceptions.py) - 커스텀 예외 클래스 정의
- [`app/error_handlers.py`](app/error_handlers.py) - 전역 에러 핸들러 구현
- [`tests/unit/test_error_handlers.py`](tests/unit/test_error_handlers.py) - 에러 핸들러 테스트

## 에러 응답 구조

모든 에러는 다음과 같은 일관된 JSON 구조로 반환됩니다:

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

### 필수 필드
- `code`: 에러 코드 (예: `INVALID_TOKEN`, `ADMIN_ONLY`)
- `message`: 사용자에게 표시할 메시지
- `status`: HTTP 상태 코드

### 선택적 필드
- `extra`: 추가적인 컨텍스트 정보 (예: `{" symbol": "AAPL"}`)
- `trace`: 스택 트레이스 (개발 환경에서만)

## 커스텀 예외 클래스

### 인증 및 권한

#### AuthenticationError (401)
```python
from app.exceptions import AuthenticationError

raise AuthenticationError(detail="인증에 실패했습니다")
```

#### InvalidTokenError (401)
```python
from app.exceptions import InvalidTokenError

raise InvalidTokenError()  # "유효하지 않은 토큰입니다"
raise InvalidTokenError(detail="토큰이 손상되었습니다")
```

#### TokenExpiredError (401)
```python
from app.exceptions import TokenExpiredError

raise TokenExpiredError()  # "토큰이 만료되었습니다"
```

#### AdminOnlyError (403)
```python
from app.exceptions import AdminOnlyError

raise AdminOnlyError()  # "관리자 권한이 필요합니다"
```

#### PremiumOnlyError (403)
```python
from app.exceptions import PremiumOnlyError

raise PremiumOnlyError()  # "프리미엄 회원 전용 기능입니다"
```

### 리소스 관련

#### ResourceNotFoundError (404)
```python
from app.exceptions import ResourceNotFoundError

raise ResourceNotFoundError(resource="사용자")
```

#### StockNotFoundError (404)
```python
from app.exceptions import StockNotFoundError

raise StockNotFoundError(symbol="AAPL")
# 응답: {"error": {"code": "STOCK_NOT_FOUND", "message": "주식 종목 (AAPL)를 찾을 수 없습니다", "extra": {"symbol": "AAPL"}}}
```

#### UserNotFoundError (404)
```python
from app.exceptions import UserNotFoundError

raise UserNotFoundError(user_id="user-123")
```

#### TaskNotFoundError (404)
```python
from app.exceptions import TaskNotFoundError

raise TaskNotFoundError(task_id="task-456")
```

### 데이터 검증

#### ValidationError (422)
```python
from app.exceptions import ValidationError

raise ValidationError(
    detail="입력 데이터가 올바르지 않습니다",
    extra={"field": "email", "issue": "invalid format"}
)
```

#### DuplicateEmailError (409)
```python
from app.exceptions import DuplicateEmailError

raise DuplicateEmailError(email="test@example.com")
```

### 외부 API

#### AlphaVantageAPIError (503)
```python
from app.exceptions import AlphaVantageAPIError

raise AlphaVantageAPIError(detail="API 키가 유효하지 않습니다")
```

#### PykrxAPIError (503)
```python
from app.exceptions import PykrxAPIError

raise PykrxAPIError(detail="데이터를 가져올 수 없습니다")
```

#### ClaudeAPIError (503)
```python
from app.exceptions import ClaudeAPIError

raise ClaudeAPIError(detail="AI 분석 서비스를 사용할 수 없습니다")
```

### 데이터 처리

#### InsufficientDataError (500)
```python
from app.exceptions import InsufficientDataError

raise InsufficientDataError(detail="최소 3년치 데이터가 필요합니다")
```

#### CalculationError (500)
```python
from app.exceptions import CalculationError

raise CalculationError(detail="베타 계산 중 오류가 발생했습니다")
```

### 비즈니스 로직

#### InvalidPeriodError (400)
```python
from app.exceptions import InvalidPeriodError

raise InvalidPeriodError(detail="기간은 1일에서 10년 사이여야 합니다")
```

#### InvalidSymbolError (400)
```python
from app.exceptions import InvalidSymbolError

raise InvalidSymbolError(symbol="INVALID")
```

### 서버 오류

#### InternalServerError (500)
```python
from app.exceptions import InternalServerError

raise InternalServerError(detail="예상치 못한 오류가 발생했습니다")
```

#### DatabaseError (500)
```python
from app.exceptions import DatabaseError

raise DatabaseError(detail="데이터베이스 연결에 실패했습니다")
```

## 사용 예시

### auth.py 적용 예시

**Before:**
```python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )

    try:
        # 토큰 검증
        pass
    except JWTError:
        raise credentials_exception
```

**After:**
```python
from app.exceptions import InvalidTokenError, TokenExpiredError

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # 토큰 검증
        pass
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError()
        else:
            raise InvalidTokenError(detail=f"토큰 검증 실패: {str(e)}")
```

### routes/admin.py 적용 예시

**Before:**
```python
@router.get("/stock/{symbol}")
async def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock
```

**After:**
```python
from app.exceptions import StockNotFoundError

@router.get("/stock/{symbol}")
async def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise StockNotFoundError(symbol=symbol)
    return stock
```

### services/alpha_vantage_loader.py 적용 예시

**Before:**
```python
def load_stock_data(symbol: str):
    try:
        data = self.client.get_stock_data(symbol)
        if not data:
            raise ValueError("No data received")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**After:**
```python
from app.exceptions import AlphaVantageAPIError, InsufficientDataError

def load_stock_data(symbol: str):
    try:
        data = self.client.get_stock_data(symbol)
        if not data:
            raise InsufficientDataError(
                detail=f"{symbol} 데이터를 가져올 수 없습니다"
            )
    except APIError as e:
        raise AlphaVantageAPIError(detail=str(e))
```

## 에러 핸들러 우선순위

에러 핸들러는 다음 순서로 적용됩니다 (구체적 → 일반적):

1. **BaseKingoException** - 커스텀 KingoPortfolio 예외
2. **RequestValidationError / ValidationError** - Pydantic 검증 에러
3. **SQLAlchemyError** - 데이터베이스 에러
4. **HTTPException** - 일반 HTTP 예외
5. **Exception** - 예상하지 못한 모든 예외 (최후의 보루)

## 로깅

모든 에러는 적절한 로그 레벨로 기록됩니다:

- **ERROR**: 커스텀 예외 (AdminOnlyError, StockNotFoundError 등)
- **WARNING**: HTTP 예외, Validation 에러
- **CRITICAL**: 예상하지 못한 일반 예외

로그 형식:
```
ERROR app.error_handlers:error_handlers.py:61 ADMIN_ONLY: 관리자 권한이 필요합니다
  path=/admin/data-status, method=GET, error_code=ADMIN_ONLY, status_code=403
```

## 테스트

전체 98개 테스트 중 17개가 에러 핸들링 관련 테스트입니다.

### 테스트 실행

```bash
# 에러 핸들러 테스트만
pytest tests/unit/test_error_handlers.py -v

# 특정 테스트 클래스
pytest tests/unit/test_error_handlers.py::TestKingoExceptionHandlers -v
```

### 테스트 구조

```
tests/unit/test_error_handlers.py
├── TestKingoExceptionHandlers (7개)
│   ├── test_base_kingo_exception_handler
│   ├── test_invalid_token_error
│   ├── test_admin_only_error
│   ├── test_stock_not_found_error
│   ├── test_duplicate_email_error
│   ├── test_validation_error_handler
│   └── test_internal_server_error_handler
├── TestGeneralExceptionHandlers (2개)
│   ├── test_general_exception_handler
│   └── test_zero_division_error_handler
├── TestErrorResponseStructure (2개)
│   ├── test_error_response_has_required_fields
│   └── test_error_response_with_extra_data
├── TestErrorHandlerIntegration (3개)
│   ├── test_auth_error_handling
│   ├── test_admin_permission_error_handling
│   └── test_validation_error_handling
└── TestCustomExceptionProperties (3개)
    ├── test_exception_has_error_code
    ├── test_exception_has_extra_data
    └── test_exception_inherits_from_http_exception
```

## 개발 환경 vs 프로덕션

### 개발 환경 (`ENVIRONMENT=development`)
- 상세한 에러 메시지 포함
- 스택 트레이스 포함
- 디버깅 정보 노출

### 프로덕션 (`ENVIRONMENT=production`)
- 일반적인 에러 메시지만 제공
- 스택 트레이스 숨김
- 보안 정보 보호

## 마이그레이션 가이드

기존 코드를 새로운 에러 핸들링 시스템으로 마이그레이션하는 방법:

### 1단계: 가장 많이 사용되는 예외부터 교체

```bash
# 현재 HTTPException 사용 현황 확인
grep -r "raise HTTPException" app/

# 우선 순위
# 1. 인증/권한 관련 (auth.py, require_admin 등)
# 2. 리소스 조회 실패 (Stock, User 등)
# 3. 외부 API 호출 실패
# 4. 데이터 검증 실패
```

### 2단계: 점진적 교체

한 파일씩 교체하고 테스트:

```python
# 1. import 추가
from app.exceptions import StockNotFoundError, AlphaVantageAPIError

# 2. HTTPException을 커스텀 예외로 교체
# Before
raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

# After
raise StockNotFoundError(symbol=symbol)

# 3. 테스트 실행
pytest tests/unit/test_admin.py -v
```

### 3단계: 테스트 업데이트

```python
# Before
assert response.status_code == 404
assert "not found" in response.json()["detail"]

# After
assert response.status_code == 404
data = response.json()
assert "error" in data
assert "not found" in data["error"]["message"].lower()
```

## 향후 개선 사항

- [ ] `routes/admin.py`에 커스텀 예외 적용 (현재 16% 커버리지)
- [ ] `services/*.py`에 커스텀 예외 적용
- [ ] Sentry 등 에러 모니터링 도구 연동
- [ ] 에러 응답 국제화 (i18n) 지원
- [ ] Rate limiting 예외 추가

## 참고 자료

- [FastAPI Exception Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [RFC 7807 - Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)

## 문의

에러 핸들링 시스템 관련 문의사항은 백엔드 팀에 문의해주세요.

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**테스트 통과**: 98/98 (100%)
