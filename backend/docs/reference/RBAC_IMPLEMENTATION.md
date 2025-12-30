# RBAC (Role-Based Access Control) 구현 문서

## 개요

KingoPortfolio에 역할 기반 접근 제어(RBAC)가 구현되었습니다.

## 사용자 역할 (Roles)

| Role | 설명 | 권한 |
|------|------|------|
| `user` | 일반 사용자 | 기본 기능 (진단, 조회) |
| `premium` | 프리미엄 회원 | 일반 기능 + 고급 분석 |
| `admin` | 관리자 | 모든 기능 + 데이터 관리 |

## 데이터베이스 스키마

### User 모델
```python
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)  # 하위 호환성 유지
    role = Column(String(20), default='user')  # 'user', 'premium', 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## 권한 체크 함수

### 1. `get_current_user()`
- **목적**: JWT 토큰 검증 및 현재 사용자 조회
- **사용**: 모든 인증이 필요한 엔드포인트
- **반환**: User 객체

### 2. `require_admin()`
- **목적**: 관리자 권한 필수
- **사용**: `/admin/*` 엔드포인트
- **에러**: 403 Forbidden "관리자 권한이 필요합니다."

```python
from app.auth import require_admin

@router.get("/admin/data-status")
async def get_data_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # 관리자만 접근 가능
):
    # ...
```

### 3. `require_premium()`
- **목적**: 프리미엄 회원 이상 권한 필수
- **사용**: 고급 분석 기능
- **에러**: 403 Forbidden "프리미엄 회원 전용 기능입니다."

```python
from app.auth import require_premium

@router.get("/analysis/comprehensive/{symbol}")
async def get_comprehensive_analysis(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_premium)  # 프리미엄 회원 전용
):
    # ...
```

## 하위 호환성 (Backward Compatibility)

기존 `is_admin` 필드는 유지되며, 자동 마이그레이션이 적용됩니다:

```python
# get_current_user() 함수 내부
if user.is_admin and user.role != 'admin':
    user.role = 'admin'
    db.commit()
```

- `is_admin = True` → 자동으로 `role = 'admin'` 설정
- 기존 admin 사용자는 로그인 시 자동으로 admin role 부여

## 마이그레이션

### 스크립트 실행
```bash
cd backend
source ../venv/bin/activate
python migrate_user_roles.py
```

### 마이그레이션 내용
1. `users` 테이블에 `role` 컬럼 추가
2. `is_admin = True` → `role = 'admin'` 업데이트
3. `is_admin = False` → `role = 'user'` 업데이트

## 테스트

### 1. 관리자 사용자 생성
```python
from app.database import SessionLocal
from app.models.user import User
from app.auth import hash_password

db = SessionLocal()

admin = User(
    email="admin@test.com",
    hashed_password=hash_password("admin123"),
    is_admin=True,
    role='admin'
)
db.add(admin)
db.commit()
```

### 2. 권한 테스트
```bash
# 일반 사용자 로그인
USER_TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com", "password":"user1234"}' | jq -r '.access_token')

# 관리자 로그인
ADMIN_TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com", "password":"admin123"}' | jq -r '.access_token')

# 일반 사용자로 admin 엔드포인트 접근 → 403 Forbidden
curl -X GET "http://localhost:8000/admin/data-status" \
  -H "Authorization: Bearer $USER_TOKEN"

# 관리자로 admin 엔드포인트 접근 → 200 OK
curl -X GET "http://localhost:8000/admin/data-status" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 보호된 엔드포인트 목록

### Admin 전용 (`require_admin`)
- `POST /admin/load-data` - 전체 데이터 수집
- `POST /admin/load-stocks` - 주식 데이터 수집
- `POST /admin/load-etfs` - ETF 데이터 수집
- `GET /admin/data-status` - 데이터 통계
- `GET /admin/progress/{task_id}` - 진행 상황 조회
- `POST /admin/alpha-vantage/*` - Alpha Vantage 데이터 수집
- `POST /admin/pykrx/*` - pykrx 데이터 수집
- `GET /admin/financial-analysis/*` - 재무 분석
- `GET /admin/valuation/*` - 밸류에이션 분석
- `GET /admin/quant/*` - 퀀트/기술 분석
- `GET /admin/report/*` - 종합 리포트
- `GET /admin/qualitative/*` - 질적 분석

### 인증 필수 (`get_current_user`)
- `GET /auth/me` - 현재 사용자 정보
- `GET /diagnosis/me` - 최신 진단 결과
- `GET /diagnosis/history/all` - 진단 이력

### 공개 (인증 불필요)
- `POST /auth/signup` - 회원가입
- `POST /auth/login` - 로그인
- `GET /survey/questions` - 설문 문항 조회

## 추후 확장

### 프리미엄 기능 추가
```python
@router.get("/analysis/comprehensive/{symbol}")
async def get_comprehensive_analysis(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_premium)  # 프리미엄 전용
):
    """종합 분석 (프리미엄 회원 전용)"""
    # ...
```

### 역할별 기능 제한
```python
def get_analysis_level(user: User) -> str:
    """사용자 역할에 따른 분석 수준 결정"""
    if user.role == 'admin':
        return 'full'  # 모든 분석
    elif user.role == 'premium':
        return 'advanced'  # 고급 분석
    else:
        return 'basic'  # 기본 분석만
```

## 보안 고려사항

1. **JWT 토큰 만료**: `settings.access_token_expire_minutes` (기본 30분)
2. **비밀번호 해싱**: Bcrypt (72바이트 제한)
3. **HTTPS 필수**: 프로덕션 환경에서는 반드시 HTTPS 사용
4. **CORS 설정**: 허용된 도메인만 API 접근 가능

## 참고 자료

- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- JWT: https://jwt.io/
- Bcrypt: https://en.wikipedia.org/wiki/Bcrypt
