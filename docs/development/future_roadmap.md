# KingoPortfolio 향후 개발 로드맵
최초작성일자: 2025-12-29
최종수정일자: 2026-01-18

## 📊 프로젝트 현황 분석

### 현재 구현된 핵심 기능
- ✅ **투자 성향 진단**: 15문항 설문 + AI 기반 프로파일링 (보수/중립/공격)
- ✅ **재무 분석**: CAGR, ROE/ROA, 부채비율, FCF 분석, 100점 재무점수
- ✅ **밸류에이션**: PER/PBR 비교, DCF (3 시나리오), DDM (배당할인모형)
- ✅ **퀀트/기술 분석**: MA, RSI, 볼린저밴드, MACD, 베타, 알파, 샤프비율
- ✅ **AI 뉴스 분석**: Claude 기반 뉴스 감성 분석
- ✅ **관리자 도구**: 한국/미국 주식 데이터 수집, 실시간 진행상황 추적

### 기술 스택
**Backend**: FastAPI + SQLAlchemy + SQLite/PostgreSQL + Alpha Vantage API + pykrx + Claude AI
**Frontend**: React 18 + Vite + React Router + Axios
**배포**: Render.com (백엔드) + Vercel (프론트엔드)

---

## 🎯 개발 우선순위별 로드맵

## Priority 1: 핵심 프로덕트 강화 (1-2개월)

### 1.1 포트폴리오 관리 기능
**현재 문제점**: 진단 결과만 제공하고 실제 보유 종목 추적 불가

**구현 사항**:
```python
# 새 모델 추가
class Portfolio(Base):
    user_id = Column(Integer, ForeignKey('users.id'))
    symbol = Column(String)
    quantity = Column(Integer)
    purchase_price = Column(Float)
    purchase_date = Column(Date)
    current_value = Column(Float)  # 실시간 업데이트

class PortfolioHistory(Base):
    portfolio_id = Column(Integer)
    date = Column(Date)
    value = Column(Float)
    return_pct = Column(Float)
```

**프론트엔드**:
- `/portfolio` 페이지: 보유 종목 현황, 수익률, 자산 배분 차트
- 매수/매도 기록 추가 기능
- 추천 포트폴리오 vs 실제 포트폴리오 비교

**예상 효과**: 사용자 retention 2배 증가, 재방문율 상승

---

### 1.2 역할 기반 접근 제어 (RBAC)
**현재 문제점**: `is_admin` 필드는 있지만 실제 권한 체크 안 함

**구현 사항**:
```python
# User 모델에 role 추가
class User(Base):
    role = Column(String, default='user')  # 'user', 'admin', 'premium'

# Dependency 개선
def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(403, "관리자 권한 필요")
    return current_user

def require_premium(current_user: User = Depends(get_current_user)):
    if current_user.role not in ['premium', 'admin']:
        raise HTTPException(403, "프리미엄 회원 전용")
    return current_user
```

**API 엔드포인트 보호**:
- `/admin/*` → `require_admin`
- `/analysis/comprehensive/*` → `require_premium` (무료는 기본 분석만)

---

### 1.3 추천 엔진 고도화
**현재 상태**: `db_recommendation_engine.py` 존재하지만 미활용

**개선 방안**:
1. **재무점수 기반 필터링**:
   ```python
   # 80점 이상만 추천
   stocks = db.query(Stock).filter(
       Stock.financial_score >= 80,
       Stock.risk_level == user.risk_profile
   ).all()
   ```

2. **현대 포트폴리오 이론 적용**:
   - 효율적 투자선(Efficient Frontier) 계산
   - 샤프비율 최대화 포트폴리오
   - 리스크 분산 최적화

3. **AI 강화**:
   ```python
   # Claude에게 포트폴리오 추천 요청
   prompt = f"""
   사용자 프로필: {user.risk_profile}, 투자금액: {user.monthly_investment}
   후보 종목: {candidates}

   최적의 포트폴리오를 구성하세요 (각 종목 비중 포함).
   """
   ```

---

## Priority 2: 한국 시장 데이터 완성도 향상 (2-3개월)

### 2.1 DART API 통합
**현재 문제점**: pykrx는 시계열만 제공, 재무제표 없음 → 한국 주식은 DCF/DDM 불가

**해결책**: 금융감독원 전자공시시스템(DART) API 통합
```python
# backend/app/services/dart_client.py
class DARTClient:
    def get_financial_statements(self, corp_code: str, year: int):
        """손익계산서, 재무상태표, 현금흐름표 조회"""

    def get_dividend_info(self, corp_code: str):
        """배당 정보 조회"""
```

**데이터베이스**:
```python
class KoreanStockFinancials(Base):
    ticker = Column(String)
    fiscal_year = Column(Integer)
    revenue = Column(BigInteger)  # 원화 단위
    operating_income = Column(BigInteger)
    net_income = Column(BigInteger)
    # ... 나머지 재무 항목
```

**구현 후**:
- ✅ 한국 주식도 DCF 밸류에이션 가능
- ✅ 한국 주식 재무점수 V2에서 Growth 항목 추가 (현재 0점)
- ✅ 미국/한국 주식 분석 기능 완전 동등화

---

### 2.2 한국 주식 기술적 분석 지원
**현재 문제점**: `AlphaVantageTimeSeries`만 지원 → 한국 주식 퀀트 분석 불가

**해결책**:
```python
# pykrx로 시계열 데이터 수집 후 DB 저장
class KoreanTimeSeries(Base):
    ticker = Column(String)
    date = Column(Date)
    open = Column(Integer)
    high = Column(Integer)
    low = Column(Integer)
    close = Column(Integer)
    volume = Column(BigInteger)

# QuantAnalyzer 수정
def get_price_data(db: Session, symbol: str, days: int = 252):
    # 한국 주식이면 KoreanTimeSeries에서 조회
    if symbol.isdigit():
        return db.query(KoreanTimeSeries).filter(...).all()
    else:
        return db.query(AlphaVantageTimeSeries).filter(...).all()
```

**벤치마크 추가**:
- KOSPI 지수 시계열 → 한국 주식의 베타/알파 계산
- KOSDAQ 지수
- 업종 지수

---

## Priority 3: UX/UI 개선 (1-2개월)

### 3.1 차트 라이브러리 통합
**현재 상태**: 차트 컴포넌트는 있지만 실제 시각화 라이브러리 미연동

**선택지**:
1. **Recharts** (권장): React 친화적, 반응형
2. **Chart.js**: 경량, 빠름
3. **ApexCharts**: 프로페셔널한 금융 차트

**구현 예시**:
```jsx
// frontend/src/components/PortfolioChart.jsx
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const PortfolioAllocation = ({ holdings }) => {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie data={holdings} dataKey="value" nameKey="symbol">
          {holdings.map((entry, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
};
```

**추가할 차트**:
- 📊 포트폴리오 자산 배분 (파이 차트)
- 📈 수익률 추이 (라인 차트)
- 📉 재무제표 트렌드 (막대 그래프)
- 🕯️ 캔들스틱 차트 (주가 기술적 분석)

---

### 3.2 Tailwind CSS 적용
**현재 문제점**: README에는 Tailwind 언급되지만 실제 미설치

**설치**:
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**마이그레이션 전략**:
1. 기존 CSS는 유지하되 신규 컴포넌트에만 Tailwind 적용
2. 점진적으로 커스텀 CSS를 Tailwind 유틸리티로 교체
3. 디자인 시스템 구축 (색상, 간격, 타이포그래피 통일)

---

### 3.3 모바일 반응형 최적화
**현재 상태**: 데스크톱 위주 레이아웃

**개선 사항**:
```css
/* Mobile First Approach */
.result-card {
  padding: 16px; /* 모바일 기본 */
}

@media (min-width: 768px) {
  .result-card {
    padding: 32px; /* 태블릿 이상 */
  }
}

/* 그리드 레이아웃 반응형 */
.admin-grid {
  grid-template-columns: 1fr; /* 모바일: 1열 */
}

@media (min-width: 768px) {
  .admin-grid {
    grid-template-columns: repeat(2, 1fr); /* 태블릿: 2열 */
  }
}

@media (min-width: 1024px) {
  .admin-grid {
    grid-template-columns: repeat(3, 1fr); /* 데스크톱: 3열 */
  }
}
```

---

## Priority 4: 알림 & 자동화 (2-3개월)

### 4.1 알림 시스템 구축
```python
# backend/app/models.py
class UserAlert(Base):
    user_id = Column(Integer, ForeignKey('users.id'))
    alert_type = Column(String)  # 'price', 'news', 'rebalance'
    symbol = Column(String)
    condition = Column(JSON)  # {"type": "price_above", "value": 100000}
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime)

# backend/app/services/alert_service.py
def check_price_alerts():
    """매 시간마다 실행되는 스케줄러"""
    alerts = db.query(UserAlert).filter(
        UserAlert.alert_type == 'price',
        UserAlert.is_active == True
    ).all()

    for alert in alerts:
        current_price = get_current_price(alert.symbol)
        if should_trigger(alert, current_price):
            send_notification(alert.user_id, alert)
```

**알림 채널**:
1. **이메일**: FastAPI-Mail 사용
2. **푸시 알림**: Firebase Cloud Messaging (FCM)
3. **인앱 알림**: 로그인 시 확인

**알림 종류**:
- 🔔 목표 가격 도달
- 📰 보유 종목 주요 뉴스
- 💼 리밸런싱 추천 (자산 배분 이탈 시)
- 📅 실적 발표일 리마인더

---

### 4.2 자동 리밸런싱 제안
```python
def analyze_portfolio_drift(user_id: int):
    """추천 배분 vs 실제 배분 차이 계산"""
    recommended = get_recommended_allocation(user_id)
    actual = get_current_allocation(user_id)

    drift = {}
    for symbol in recommended:
        drift[symbol] = actual[symbol] - recommended[symbol]

    # 5% 이상 차이나면 알림
    if any(abs(d) > 0.05 for d in drift.values()):
        suggest_rebalancing(user_id, drift)
```

---

## Priority 5: B2B & API 서비스화 (3-6개월)

### 5.1 API 서비스 구축
**목표**: 분석 API를 외부 서비스에 제공

```python
# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/api/v1/analysis/{symbol}")
@limiter.limit("10/minute")  # 무료: 10req/min
async def get_stock_analysis(symbol: str, api_key: str):
    """API 키 기반 분석 제공"""
    subscription = verify_api_key(api_key)

    if subscription.tier == 'free':
        return basic_analysis(symbol)
    elif subscription.tier == 'pro':
        return comprehensive_analysis(symbol)
```

**구독 모델**:
| 티어 | 가격 | 요청 한도 | 기능 |
|------|------|-----------|------|
| Free | 무료 | 100 req/day | 기본 재무 분석 |
| Pro | $49/월 | 10,000 req/day | 전체 분석 + 실시간 |
| Enterprise | 협의 | 무제한 | 화이트라벨 + 커스텀 |

---

### 5.2 멀티테넌트 아키텍처
**목표**: 증권사/은행에 화이트라벨 솔루션 제공

```python
class Organization(Base):
    """증권사/은행 조직"""
    name = Column(String)
    domain = Column(String, unique=True)  # kb.kingo.ai
    branding = Column(JSON)  # 로고, 색상
    tier = Column(String)  # 'basic', 'enterprise'

class User(Base):
    org_id = Column(Integer, ForeignKey('organizations.id'))
    # ... (기존 필드)
```

**기능**:
- 🏢 조직별 독립 데이터베이스 (또는 스키마 분리)
- 🎨 커스터마이징 가능한 브랜딩
- 📊 조직별 사용 통계 대시보드
- 💳 조직 단위 결제

---

## Priority 6: 인프라 & DevOps (지속적)

### 6.1 캐싱 레이어 추가
**현재 문제점**: 동일한 분석 요청을 매번 재계산

**해결책**: Redis 캐싱
```python
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379)

def cache_result(ttl=3600):
    """분석 결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cached = redis_client.get(cache_key)

            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@cache_result(ttl=1800)  # 30분 캐싱
def get_comprehensive_analysis(symbol: str):
    # 무거운 계산...
```

**캐싱 전략**:
- 주가 데이터: 15분 TTL (장중), 1일 TTL (장마감 후)
- 재무제표: 1일 TTL
- 뉴스 감성: 1시간 TTL

---

### 6.2 CI/CD 파이프라인
**GitHub Actions 워크플로우**:
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest tests/

      - name: Run Frontend Tests
        run: |
          cd frontend
          npm install
          npm run test

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Vercel
        run: |
          vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

---

### 6.3 모니터링 & 로깅
**도구 선택**:
1. **에러 트래킹**: Sentry
2. **성능 모니터링**: New Relic / Datadog
3. **로그 집계**: ELK Stack (Elasticsearch, Logstash, Kibana)
4. **사용자 분석**: Mixpanel / Amplitude

**구현 예시**:
```python
# backend/app/main.py
import sentry_sdk

sentry_sdk.init(
    dsn="https://...",
    traces_sample_rate=0.1,
    environment="production"
)

# 로깅 구조화
import structlog

logger = structlog.get_logger()
logger.info("user_login", user_id=123, ip="1.2.3.4")
```

---

## 🚀 Quick Wins (즉시 구현 가능)

### 1. 비밀번호 재설정 기능
```python
@router.post("/auth/forgot-password")
async def forgot_password(email: str):
    user = db.query(User).filter(User.email == email).first()
    if user:
        reset_token = generate_reset_token(user.id)
        send_email(email, f"Reset link: /reset/{reset_token}")
```

### 2. 사용자 프로필 페이지
```jsx
// frontend/src/pages/ProfilePage.jsx
const ProfilePage = () => {
  return (
    <div>
      <h2>내 정보</h2>
      <form>
        <input name="name" defaultValue={user.name} />
        <input name="email" defaultValue={user.email} disabled />
        <button>수정</button>
      </form>

      <h3>투자 성향</h3>
      <p>{user.risk_profile}</p>
      <button onClick={() => navigate('/survey')}>재진단하기</button>
    </div>
  );
};
```

### 3. 데이터 내보내기 (CSV/Excel)
```python
@router.get("/admin/export/stocks")
async def export_stocks(format: str = 'csv'):
    stocks = db.query(Stock).all()

    if format == 'csv':
        return generate_csv(stocks)
    elif format == 'xlsx':
        return generate_excel(stocks)
```

### 4. 공개 랜딩 페이지
```jsx
// frontend/src/pages/LandingPage.jsx
const LandingPage = () => {
  return (
    <div>
      <section className="hero">
        <h1>AI 기반 투자 포트폴리오 추천</h1>
        <p>15개 질문으로 당신만의 투자 전략을 찾아보세요</p>
        <button onClick={() => navigate('/signup')}>무료로 시작하기</button>
      </section>

      <section className="features">
        <div>재무 분석</div>
        <div>밸류에이션</div>
        <div>AI 뉴스 분석</div>
      </section>
    </div>
  );
};
```

### 5. API Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.get("/api/stocks")
@limiter.limit("100/hour")
async def get_stocks():
    # ...
```

---

## 📈 KPI 달성 전략

**목표 (24개월 내)**:
- 👥 누적 사용자: 50만명
- 💰 운용자산(AUM): 2.5조원
- 📊 활성 사용자율: 30%

### Phase 1 (0-6개월): Product-Market Fit
- 포트폴리오 관리 기능 출시
- 한국 시장 데이터 완성도 100%
- 모바일 UX 최적화
- **목표**: 1만명 가입, 10억원 AUM

### Phase 2 (6-12개월): Growth
- 알림 시스템으로 retention 향상
- 유료 구독 모델 출시 (프리미엄 분석)
- 마케팅 투자 (SEO, 소셜 미디어)
- **목표**: 10만명 가입, 500억원 AUM

### Phase 3 (12-18개월): Expansion
- B2B API 서비스 론칭
- 증권사 파트너십 (화이트라벨)
- 자동 리밸런싱 등 고급 기능
- **목표**: 30만명 가입, 1.5조원 AUM

### Phase 4 (18-24개월): Scale
- 멀티테넌트 플랫폼 완성
- 기관 투자자 대시보드
- AI 챗봇 투자 어드바이저
- **목표**: 50만명 가입, 2.5조원 AUM

---

## 💡 기술 부채 정리

### 즉시 개선 필요
1. ❌ `is_admin` 필드 있지만 권한 체크 안 함 → RBAC 구현
2. ❌ Frontend에 Tailwind 없음 → 설치 및 마이그레이션
3. ❌ 테스트 코드 부족 → pytest 테스트 작성
4. ❌ 에러 핸들링 일관성 없음 → 전역 에러 핸들러
5. ❌ API 문서화 부족 → Swagger 자동 생성 개선

### 중장기 개선
- 데이터베이스: SQLite → PostgreSQL (프로덕션)
- 인증: JWT → OAuth2 + refresh token
- 프론트엔드: 상태관리 Context API → Zustand/Recoil
- 아키텍처: Monolith → Microservices (필요 시)

---

## 🎓 학습 & 성장 전략

### 팀 역량 강화
- **백엔드**: FastAPI 고급 기능 (WebSocket, Dependency Injection)
- **프론트엔드**: React 성능 최적화, SSR (Next.js)
- **DevOps**: Kubernetes, Docker Compose
- **AI/ML**: 자체 예측 모델 개발 (scikit-learn, TensorFlow)

### 코드 품질
- 코드 리뷰 프로세스 확립
- Pre-commit hooks (Black, ESLint, Prettier)
- 문서화 자동화 (Sphinx, JSDoc)

---

## 결론

KingoPortfolio는 **투자 진단 도구에서 종합 자산관리 플랫폼**으로 진화하고 있습니다.

**강점**:
- ✅ 전문적인 금융 분석 기능 (DCF, 기술적 분석)
- ✅ AI 통합으로 차별화
- ✅ 확장 가능한 아키텍처

**단기 집중 영역**:
1. 포트폴리오 관리 (사용자 retention)
2. 한국 시장 완성도 (DART API)
3. UX/UI 개선 (모바일, 차트)

**장기 비전**:
- B2B SaaS 플랫폼
- 화이트라벨 솔루션
- 글로벌 시장 확장

50만명 사용자와 2.5조원 AUM은 **도전적이지만 달성 가능한 목표**입니다. 핵심은 **사용자에게 실질적 가치를 제공하는 기능에 집중**하는 것입니다.
