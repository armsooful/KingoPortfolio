# Testing Documentation

## 개요

KingoPortfolio 백엔드의 pytest 기반 테스트 스위트입니다.

## 테스트 통계

- **전체 테스트**: 81개
- **통과율**: 100% (81/81)
- **코드 커버리지**: 32%
- **테스트 실행 시간**: ~29초

## 테스트 구조

```
backend/tests/
├── conftest.py           # Pytest 설정 및 공통 fixture
├── unit/                 # 단위 테스트
│   ├── test_auth.py             # 인증 관련 테스트 (16개)
│   ├── test_rbac.py             # RBAC 권한 테스트 (13개)
│   ├── test_financial_analysis.py  # 재무 분석 테스트 (13개)
│   ├── test_valuation.py        # 밸류에이션 테스트 (18개)
│   └── test_quant_analysis.py   # 퀀트 분석 테스트 (21개)
└── integration/          # 통합 테스트 (TODO)
```

## 설치 및 실행

### 1. 테스트 라이브러리 설치

```bash
cd backend
source ../venv/bin/activate
pip install pytest pytest-asyncio pytest-cov httpx faker
```

### 2. 전체 테스트 실행

```bash
pytest -v
```

### 3. 커버리지 리포트 포함

```bash
pytest --cov=app --cov-report=html
```

HTML 리포트는 `htmlcov/index.html`에서 확인 가능합니다.

### 4. 특정 마커로 테스트 실행

```bash
# 인증 테스트만
pytest -m auth

# 재무 분석 테스트만
pytest -m financial

# 밸류에이션 테스트만
pytest -m valuation

# 퀀트 분석 테스트만
pytest -m quant

# 단위 테스트만
pytest -m unit

# 통합 테스트만
pytest -m integration
```

## 테스트 상세 내용

### 1. 인증 테스트 (test_auth.py)

#### TestPasswordHashing
- ✅ 비밀번호 해싱
- ✅ 비밀번호 검증 (정상/실패)
- ✅ 72바이트 초과 비밀번호 처리

#### TestJWTToken
- ✅ JWT 토큰 생성
- ✅ JWT 토큰 디코딩
- ✅ 토큰 만료 처리

#### TestAuthentication
- ✅ 회원가입 (성공/중복 이메일/짧은 비밀번호)
- ✅ 로그인 (성공/잘못된 비밀번호/존재하지 않는 사용자)
- ✅ 현재 사용자 조회 (성공/토큰 없음/잘못된 토큰)

### 2. RBAC 테스트 (test_rbac.py)

#### TestRBAC
- ✅ 사용자 역할 할당 (user, admin, premium)
- ✅ 관리자 접근 허용
- ✅ 일반 사용자 접근 거부 (403)
- ✅ 프리미엄 사용자의 admin 접근 거부
- ✅ 미인증 사용자 접근 거부 (401)
- ✅ is_admin 하위 호환성
- ✅ 로그인 시 role 자동 마이그레이션

#### TestAdminEndpoints (파라미터화)
- ✅ 모든 admin 엔드포인트 인증 필수
- ✅ 일반 사용자 거부
- ✅ 관리자 허용

### 3. 재무 분석 테스트 (test_financial_analysis.py)

#### TestCagrCalculation
- ✅ CAGR 양의 성장률 계산
- ✅ CAGR 음의 성장률 계산
- ✅ CAGR 0년 기간 처리
- ✅ CAGR 0 시작값 처리
- ✅ CAGR 동일값 처리

#### TestFinancialRatios
- ✅ ROE 계산
- ✅ ROE 자본 0 처리
- ✅ ROA 계산
- ✅ 이익률 계산 (gross, operating, net)
- ✅ 부채비율 계산

#### TestFinancialScore
- ✅ 점수 범위 검증 (0-100)
- ✅ 우수한 재무지표 → 높은 점수
- ✅ 부진한 재무지표 → 낮은 점수

#### TestFinancialAnalysisEndpoint
- ✅ 인증 필요 (401)
- ✅ 관리자 권한 필요 (403)
- ✅ 관리자 접근 가능
- ✅ 재무 점수 V2 응답 구조

### 4. 밸류에이션 테스트 (test_valuation.py)

#### TestIndustryMultiples
- ✅ 기술 산업 멀티플 조회
- ✅ 금융 산업 멀티플 조회
- ✅ 알 수 없는 산업 → 기본값 반환

#### TestValuationComparison
- ✅ 저평가 판정
- ✅ 고평가 판정
- ✅ 적정 평가 판정

#### TestValuationEndpoints
- ✅ 멀티플 비교 인증/권한 체크
- ✅ 종합 밸류에이션 공개 접근 (보안 이슈 문서화)
- ✅ DCF 엔드포인트
- ✅ DDM 엔드포인트

#### TestDCFCalculations
- ✅ FCF 성장 예측
- ✅ 터미널 밸류 계산
- ✅ 현재가치 할인

#### TestDDMCalculations
- ✅ 고든 성장 모델
- ✅ DDM 무효 조건 (성장률 > 요구수익률)

### 5. 퀀트 분석 테스트 (test_quant_analysis.py)

#### TestVolatilityCalculations
- ✅ 변동성 계산 (표준편차)
- ✅ 연환산 변동성

#### TestReturnsCalculations
- ✅ 단순 수익률
- ✅ 로그 수익률
- ✅ 누적 수익률

#### TestBetaCalculations
- ✅ 베타 양의 상관관계
- ✅ 베타 해석 (aggressive, neutral, defensive, inverse)

#### TestSharpeRatio
- ✅ 샤프 비율 계산
- ✅ 샤프 비율 해석 (우수/양호/부족)

#### TestMovingAverages
- ✅ 단순 이동평균
- ✅ 골든 크로스 시그널
- ✅ 데드 크로스 시그널

#### TestRSI
- ✅ RSI 계산
- ✅ RSI 과매수 (>70)
- ✅ RSI 과매도 (<30)

#### TestQuantAnalysisEndpoints
- ✅ 퀀트 리스크 인증/권한 체크
- ✅ 종합 퀀트 분석 공개 접근 (보안 이슈 문서화)
- ✅ 응답 구조 검증

## Fixtures

### conftest.py

#### 데이터베이스 Fixtures
- `db`: 테스트용 데이터베이스 세션 (function scope)

#### 테스트 사용자 Fixtures
- `test_user`: 일반 사용자 (role='user')
- `test_admin`: 관리자 (role='admin', is_admin=True)
- `test_premium_user`: 프리미엄 사용자 (role='premium')

#### 인증 토큰 Fixtures
- `user_token`: 일반 사용자 JWT 토큰
- `admin_token`: 관리자 JWT 토큰
- `premium_token`: 프리미엄 사용자 JWT 토큰

#### HTTP 헤더 Fixtures
- `auth_headers`: 일반 사용자 Authorization 헤더
- `admin_headers`: 관리자 Authorization 헤더
- `premium_headers`: 프리미엄 사용자 Authorization 헤더

#### API 클라이언트
- `client`: FastAPI TestClient

## 코드 커버리지

### 높은 커버리지 (>90%)
- ✅ `app/models/__init__.py`: 100%
- ✅ `app/routes/__init__.py`: 100%
- ✅ `app/schemas.py`: 100%
- ✅ `app/models/securities.py`: 99%
- ✅ `app/models/alpha_vantage.py`: 96%
- ✅ `app/config.py`: 96%
- ✅ `app/models/user.py`: 94%
- ✅ `app/models.py`: 93%

### 중간 커버리지 (30-90%)
- 🟡 `app/auth.py`: 87%
- 🟡 `app/routes/auth.py`: 85%
- 🟡 `app/main.py`: 72%
- 🟡 `app/database.py`: 64%
- 🟡 `app/services/valuation.py`: 44%

### 낮은 커버리지 (<30%)
- 🔴 `app/routes/diagnosis.py`: 33%
- 🔴 `app/progress_tracker.py`: 33%
- 🔴 `app/crud.py`: 35%
- 🔴 `app/data_collector.py`: 27%
- 🔴 `app/services/claude_service.py`: 24%
- 🔴 `app/routes/admin.py`: 24%
- 🔴 `app/diagnosis.py`: 19%
- 🔴 `app/services/financial_analyzer.py`: 16%
- 🔴 `app/services/quant_analyzer.py`: 16%
- 🔴 `app/services/data_loader.py`: 15%
- 🔴 `app/services/alpha_vantage_client.py`: 13%
- 🔴 `app/services/pykrx_loader.py`: 7%
- 🔴 `app/services/alpha_vantage_loader.py`: 7%
- 🔴 `app/routes/survey.py`: 0%
- 🔴 `app/db_recommendation_engine.py`: 0%

## 향후 개선 사항

### 1. 커버리지 확대
- [ ] Admin 엔드포인트 통합 테스트 추가 (현재 24%)
- [ ] Data loader 테스트 추가 (현재 7-15%)
- [ ] 진단(diagnosis) 기능 테스트 (현재 19-33%)
- [ ] Survey 테스트 추가 (현재 0%)

### 2. 보안 이슈 해결
- [ ] `/admin/valuation/comprehensive/{symbol}` 인증 추가
- [ ] `/admin/quant/comprehensive/{symbol}` 인증 추가

### 3. 테스트 타입 확장
- [ ] E2E 테스트 추가
- [ ] 성능 테스트 추가
- [ ] 부하 테스트 추가

### 4. CI/CD 통합
- [ ] GitHub Actions 설정
- [ ] 자동 테스트 실행
- [ ] 커버리지 리포트 자동 업로드

## 테스트 작성 가이드

### 테스트 마커 사용

```python
@pytest.mark.unit  # 단위 테스트
@pytest.mark.integration  # 통합 테스트
@pytest.mark.auth  # 인증 관련
@pytest.mark.admin  # 관리자 기능
@pytest.mark.financial  # 재무 분석
@pytest.mark.valuation  # 밸류에이션
@pytest.mark.quant  # 퀀트 분석
```

### Fixture 활용

```python
def test_admin_access(client, admin_headers):
    """관리자 권한 테스트"""
    response = client.get("/admin/data-status", headers=admin_headers)
    assert response.status_code == 200
```

### 파라미터화 테스트

```python
@pytest.mark.parametrize("endpoint", [
    "/admin/data-status",
    "/admin/progress/test-id"
])
def test_endpoints_require_auth(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 401
```

## 문제 해결

### 1. 테스트 DB 초기화 실패

```bash
# 테스트 DB 파일 삭제
rm test.db

# 다시 실행
pytest
```

### 2. Import 에러

```bash
# PYTHONPATH 설정
export PYTHONPATH=$PYTHONPATH:/Users/changrim/KingoPortfolio/backend

# 또는 pytest.ini의 pythonpath 설정 확인
```

### 3. Fixture 못 찾음

`conftest.py`가 올바른 위치에 있는지 확인:
- `tests/conftest.py` (전역)
- `tests/unit/conftest.py` (unit 전용, 선택사항)

## 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [FastAPI 테스팅 가이드](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)

## 마지막 업데이트

- **날짜**: 2025-12-29
- **작성자**: Claude Code (AI Assistant)
- **버전**: 1.0.0
