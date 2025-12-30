# API Rate Limiting

## 개요

KingoPortfolio API는 API 남용을 방지하고 서버 리소스를 보호하기 위해 요청 속도 제한(Rate Limiting)을 구현하고 있습니다. slowapi 라이브러리를 사용하여 엔드포인트별로 다른 제한을 적용합니다.

## 주요 파일

- [`app/rate_limiter.py`](app/rate_limiter.py) - Rate Limiter 설정 및 클라이언트 식별자 추출 로직
- [`app/main.py`](app/main.py) - Rate Limiter 미들웨어 통합 (lines 145-147)
- [`app/routes/auth.py`](app/routes/auth.py) - 인증 엔드포인트에 Rate Limit 적용
- [`app/routes/diagnosis.py`](app/routes/diagnosis.py) - 진단 엔드포인트에 Rate Limit 적용

## 기능

### 1. 클라이언트 식별

Rate Limiter는 다음 우선순위로 클라이언트를 식별합니다:

1. **인증된 사용자 ID** - 로그인한 사용자는 사용자 ID로 추적
2. **X-Forwarded-For 헤더** - 프록시 환경에서 실제 클라이언트 IP 추출
3. **원격 주소** - 직접 연결 시 IP 주소 사용

```python
def get_client_identifier(request: Request) -> str:
    """클라이언트 식별자 추출"""
    # 1. 인증된 사용자
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # 2. X-Forwarded-For 헤더
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # 3. 원격 주소
    return get_remote_address(request)
```

### 2. Rate Limit 프리셋

엔드포인트 유형별로 사전 정의된 제한을 사용합니다:

```python
class RateLimits:
    # 인증 관련 (보안 중요)
    AUTH_SIGNUP = "5/hour"           # 회원가입: 시간당 5회
    AUTH_LOGIN = "10/minute"         # 로그인: 분당 10회
    AUTH_REFRESH = "20/hour"         # 토큰 갱신: 시간당 20회
    AUTH_PASSWORD_RESET = "3/hour"   # 비밀번호 재설정: 시간당 3회

    # 진단 관련
    DIAGNOSIS_SUBMIT = "10/hour"     # 진단 제출: 시간당 10회
    DIAGNOSIS_READ = "100/hour"      # 진단 조회: 시간당 100회

    # 데이터 조회
    DATA_READ = "200/hour"           # 데이터 조회: 시간당 200회
    DATA_EXPORT = "20/hour"          # 데이터 내보내기: 시간당 20회

    # 관리자
    ADMIN_WRITE = "100/hour"         # 관리자 작성: 시간당 100회
    ADMIN_READ = "500/hour"          # 관리자 조회: 시간당 500회

    # 공개 API
    PUBLIC_API = "100/hour"          # 공개 API: 시간당 100회

    # AI 분석 (비용 발생)
    AI_ANALYSIS = "5/hour"           # AI 분석: 시간당 5회
```

### 3. 적용된 엔드포인트

#### 인증 엔드포인트

| 엔드포인트 | 제한 | 이유 |
|-----------|------|------|
| `POST /auth/signup` | 시간당 5회 | 스팸 계정 생성 방지 |
| `POST /auth/login` | 분당 10회 | 브루트 포스 공격 방지 |
| `POST /auth/forgot-password` | 시간당 3회 | 이메일 스팸 방지 |

#### 진단 엔드포인트

| 엔드포인트 | 제한 | 이유 |
|-----------|------|------|
| `POST /diagnosis/submit` | 시간당 10회 | 서버 리소스 보호 |
| `GET /diagnosis/{id}/export/csv` | 시간당 20회 | 대용량 데이터 생성 제한 |
| `GET /diagnosis/{id}/export/excel` | 시간당 20회 | 대용량 데이터 생성 제한 |

## 사용 방법

### 1. 엔드포인트에 Rate Limit 적용

```python
from fastapi import APIRouter, Request
from app.rate_limiter import limiter, RateLimits

router = APIRouter()

@router.post("/signup")
@limiter.limit(RateLimits.AUTH_SIGNUP)
async def signup(
    request: Request,  # 필수: slowapi가 클라이언트를 식별하기 위해 필요
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    # 회원가입 로직
    pass
```

**주의사항**:
- `request: Request` 파라미터가 **반드시 첫 번째 위치**에 있어야 합니다
- slowapi 데코레이터는 이 파라미터를 통해 클라이언트를 식별합니다

### 2. 커스텀 Rate Limit 사용

```python
@router.get("/custom-endpoint")
@limiter.limit("30/minute")  # 분당 30회로 커스텀 제한
async def custom_endpoint(request: Request):
    pass
```

### 3. 여러 제한 적용

```python
@router.post("/important-action")
@limiter.limit("5/minute")    # 분당 5회
@limiter.limit("50/hour")     # 시간당 50회
async def important_action(request: Request):
    # 두 제한 모두 적용됨
    pass
```

## Rate Limit 응답

### 429 Too Many Requests

Rate Limit을 초과하면 `429 Too Many Requests` 에러가 반환됩니다:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "detail": "5 per 1 hour",
  "retry_after": 3600
}
```

**응답 필드**:
- `error`: 에러 타입
- `message`: 사용자 친화적인 메시지
- `detail`: 구체적인 제한 (예: "5 per 1 hour")
- `retry_after`: 재시도 가능 시간 (초)

### HTTP 헤더

slowapi는 다음 헤더를 자동으로 추가합니다:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1640995200
```

- `X-RateLimit-Limit`: 최대 허용 요청 수
- `X-RateLimit-Remaining`: 남은 요청 수
- `X-RateLimit-Reset`: 제한 리셋 시간 (UNIX 타임스탬프)

## 프로덕션 설정

### Redis 스토리지 사용

개발 환경에서는 메모리 스토리지를 사용하지만, 프로덕션에서는 Redis를 사용해야 합니다:

```python
# app/rate_limiter.py
limiter = Limiter(
    key_func=get_client_identifier,
    default_limits=["1000/hour"],
    storage_uri="redis://localhost:6379"  # Redis 연결
    # 또는 환경변수 사용:
    # storage_uri=os.getenv("REDIS_URL", "memory://")
)
```

**Redis 설치**:
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

**Python 의존성**:
```bash
pip install redis
```

### 환경변수 설정

`.env` 파일에 추가:

```env
# Rate Limiting
REDIS_URL=redis://localhost:6379
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=redis  # 또는 memory
```

## 테스트

### 단위 테스트

```python
def test_rate_limit_constants():
    """Rate Limit 상수 확인"""
    from app.rate_limiter import RateLimits

    assert RateLimits.AUTH_SIGNUP == "5/hour"
    assert RateLimits.AUTH_LOGIN == "10/minute"
```

### 통합 테스트

```python
def test_login_rate_limit(client):
    """로그인 Rate Limit 테스트"""
    # 첫 번째 요청 - 성공
    response1 = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response1.status_code == 200

    # 여러 번 시도 (분당 10회 이내)
    for i in range(5):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
```

### 실제 Rate Limit 초과 테스트

```python
@pytest.mark.slow
def test_rate_limit_exceeded():
    """실제로 제한을 초과하여 429 에러 확인"""
    # 시간당 5회 제한을 초과하여 요청
    for i in range(6):
        response = client.post("/auth/signup", json={
            "email": f"user{i}@example.com",
            "password": "password123"
        })
        if i < 5:
            assert response.status_code in [201, 409]
        else:
            assert response.status_code == 429  # 6번째는 차단
```

## 모니터링

### 로그 확인

Rate Limit 초과 시 로그가 자동으로 기록됩니다:

```
WARNING: Rate limit exceeded for client 192.168.1.1: 5 per 1 hour
```

### 메트릭 수집

Prometheus 등의 메트릭 시스템과 통합 가능:

```python
from prometheus_client import Counter

rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total number of rate limit exceeded events',
    ['endpoint', 'client']
)

def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    rate_limit_exceeded.labels(
        endpoint=request.url.path,
        client=get_client_identifier(request)
    ).inc()
    # ... 에러 응답
```

## 보안 고려사항

### 1. IP 스푸핑 방지

프록시 환경에서는 `X-Forwarded-For` 헤더를 신뢰하기 전에 검증이 필요합니다:

```python
def get_client_identifier(request: Request) -> str:
    # Cloudflare, AWS ALB 등 신뢰할 수 있는 프록시만 허용
    trusted_proxies = ["cloudflare", "aws-alb"]

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and is_trusted_proxy(request):
        return forwarded.split(",")[0].strip()

    return get_remote_address(request)
```

### 2. 분산 서비스 고려

여러 서버 인스턴스를 운영하는 경우 **반드시 Redis**를 사용해야 합니다. 메모리 스토리지는 각 인스턴스마다 별도로 카운트되므로 효과가 없습니다.

### 3. 봇 감지

반복적으로 Rate Limit을 초과하는 클라이언트는 자동으로 차단:

```python
# 추후 구현 예정
RATE_LIMIT_BAN_THRESHOLD = 10  # 10회 초과 시 24시간 차단
RATE_LIMIT_BAN_DURATION = 86400  # 24시간
```

## 문제 해결

### Rate Limit이 작동하지 않음

1. **Request 파라미터 확인**: 함수 시그니처에 `request: Request`가 **첫 번째 위치**에 있는지 확인
2. **미들웨어 등록 확인**: `app.state.limiter` 설정 확인
3. **slowapi 설치 확인**: `pip install slowapi`

### Redis 연결 실패

```python
# 에러: redis.exceptions.ConnectionError
# 해결: Redis 서버 상태 확인
redis-cli ping  # 응답: PONG
```

### 테스트 환경에서 Rate Limit 비활성화

```python
# conftest.py
@pytest.fixture(autouse=True)
def disable_rate_limit(monkeypatch):
    """테스트 환경에서 Rate Limit 비활성화"""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
```

## 향후 개선 사항

- [ ] Redis Cluster 지원 (고가용성)
- [ ] 동적 Rate Limit (사용자 등급별 다른 제한)
- [ ] Rate Limit 초과 시 자동 차단 (IP Ban)
- [ ] 관리자 대시보드 (Rate Limit 모니터링)
- [ ] WebSocket 연결에 대한 Rate Limiting
- [ ] GraphQL 쿼리 복잡도 기반 제한

## 기술 스택

### 의존성

```
slowapi>=0.1.9
limits>=2.3
redis>=5.0.0  # 프로덕션
```

### 설치

```bash
pip install slowapi limits
# 프로덕션
pip install redis
```

## 관련 문서

- [데이터 내보내기 가이드](EXPORT.md)
- [프로필 관리 가이드](PROFILE.md)
- [SEO 최적화 가이드](SEO.md)
- [에러 핸들링 시스템](ERROR_HANDLING.md)

## 참고 자료

### 공식 문서
- [slowapi GitHub](https://github.com/laurentS/slowapi)
- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Redis Documentation](https://redis.io/documentation)

### Rate Limiting 패턴
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Leaky Bucket Algorithm](https://en.wikipedia.org/wiki/Leaky_bucket)
- [Fixed Window vs Sliding Window](https://konghq.com/blog/how-to-design-a-scalable-rate-limiting-algorithm)

## 통계

### 코드 변경

- **추가된 파일**: 2개
  - `app/rate_limiter.py` (99 lines)
  - `tests/unit/test_rate_limiting.py` (200 lines)

- **수정된 파일**: 3개
  - `app/main.py`: +3 lines (limiter 통합)
  - `app/routes/auth.py`: +3 decorators (signup, login, forgot-password)
  - `app/routes/diagnosis.py`: +3 decorators (submit, export csv, export excel)

### Rate Limit 설정

- **총 프리셋**: 12개
- **적용된 엔드포인트**: 6개
- **최소 제한**: 시간당 3회 (비밀번호 재설정)
- **최대 제한**: 시간당 500회 (관리자 읽기)

## 문의

Rate Limiting 관련 문의사항은 백엔드 팀에 문의해주세요.

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**작성자**: Claude Code (AI Assistant)
