# 복합 등급 체계 가이드

KingoPortfolio는 **VIP 등급**과 **멤버십 플랜**을 결합한 복합 등급 체계를 사용하여 사용자에게 차등화된 서비스를 제공합니다.

## 📊 등급 체계 개요

### 1. VIP 등급 (활동 기반, 자동 부여)

사용자의 활동 점수 또는 총 자산에 따라 자동으로 결정되는 등급입니다.

| 등급 | 필요 조건 | 포트폴리오 | 과거 데이터 | 활동 점수 배율 |
|------|----------|-----------|------------|---------------|
| 🥉 **Bronze** | 기본 등급 | 최대 3개 | 3개월 | 1.0x |
| 🥈 **Silver** | 활동 점수 100점 이상<br/>또는 자산 5천만원 이상 | 최대 5개 | 6개월 | 1.2x |
| 🥇 **Gold** | 활동 점수 500점 이상<br/>또는 자산 1억원 이상 | 최대 10개 | 1년 | 1.5x |
| 💎 **Platinum** | 활동 점수 1,000점 이상<br/>또는 자산 5억원 이상 | 최대 20개 | 2년 | 2.0x |
| 💠 **Diamond** | 활동 점수 3,000점 이상<br/>또는 자산 10억원 이상 | 최대 100개 | 5년 | 3.0x |

### 2. 멤버십 플랜 (유료 구독)

사용자가 선택하는 유료 구독 플랜입니다.

| 플랜 | 가격 | AI 요청 | 리포트 | 고급 차트 | PDF 내보내기 | 실시간 데이터 | 맞춤 알림 |
|------|------|---------|--------|----------|--------------|--------------|----------|
| 🆓 **Free** | 무료 | 월 10회 | 월 2개 | ❌ | ❌ | ❌ | ❌ |
| 🌱 **Starter** | 월 9,900원 | 월 50회 | 월 10개 | ✅ | ✅ | ❌ | ❌ |
| 🚀 **Pro** | 월 29,900원 | 월 200회 | 월 50개 | ✅ | ✅ | ✅ | ✅ |
| 🏢 **Enterprise** | 월 99,900원 | 월 1000회 | 월 500개 | ✅ | ✅ | ✅ | ✅ + 컨설팅 |

## 🎯 활동 점수 획득 방법

활동 점수는 다음과 같은 활동을 통해 획득할 수 있습니다:

| 활동 | 기본 점수 | VIP 배율 적용 | 설명 |
|------|----------|--------------|------|
| 포트폴리오 생성 | 50점 | ✅ | 새로운 포트폴리오를 생성하면 획득 |
| 진단 완료 | 30점 | ✅ | 투자 성향 진단을 완료하면 획득 |
| 리포트 생성 | 20점 | ✅ | 투자 리포트를 생성하면 획득 |
| 매일 로그인 | 5점 | ✅ | 하루 1회 로그인 시 획득 |
| 프로필 완성 | 100점 | ❌ | 프로필을 100% 작성하면 1회 획득 |

**VIP 배율**: 높은 VIP 등급일수록 동일한 활동으로 더 많은 점수를 획득합니다.
- Bronze: 1.0x
- Silver: 1.2x (기본 50점 → 60점)
- Gold: 1.5x (기본 50점 → 75점)
- Platinum: 2.0x (기본 50점 → 100점)
- Diamond: 3.0x (기본 50점 → 150점)

## 🔧 API 엔드포인트

### 1. 권한 조회
```http
GET /auth/tier/permissions
Authorization: Bearer {token}
```

**응답 예시:**
```json
{
  "user_id": "usr_abc123xyz",
  "email": "user@example.com",
  "vip_tier": "silver",
  "activity_points": 150,
  "membership_plan": "starter",
  "membership_status": {
    "plan": "starter",
    "is_active": true,
    "start_date": "2026-01-01T00:00:00Z",
    "end_date": "2026-02-01T00:00:00Z",
    "days_remaining": 30
  },
  "permissions": {
    "max_portfolios": 5,
    "historical_data_months": 6,
    "activity_point_multiplier": 1.2,
    "monthly_ai_requests": 50,
    "monthly_reports": 10,
    "advanced_charts": true,
    "export_reports": true,
    "real_time_data": false,
    "custom_alerts": false,
    "current_ai_requests": 3,
    "current_reports": 1
  }
}
```

### 2. 등급 상태 조회
```http
GET /auth/tier/status
Authorization: Bearer {token}
```

**응답 예시:**
```json
{
  "current_tier": "silver",
  "activity_points": 150,
  "total_assets_만원": 3000,
  "next_tier": {
    "tier": "gold",
    "required_activity_points": 500,
    "remaining_activity_points": 350,
    "required_total_assets_만원": 10000,
    "remaining_total_assets_만원": 7000,
    "progress_percentage": 30
  },
  "membership_plan": "starter",
  "membership_active": true
}
```

### 3. VIP 등급 업그레이드 테스트 (개발/데모용)
```http
POST /auth/tier/test-upgrade?points=150
Authorization: Bearer {token}
```

**주의**: 이 엔드포인트는 테스트/데모용입니다. 프로덕션 환경에서는 제거하거나 admin 권한으로 제한해야 합니다.

## 💻 코드 사용 예시

### Python (Backend)

```python
from app.models.user import User
from app.utils.tier_permissions import (
    get_user_permissions,
    can_create_portfolio,
    can_request_ai_analysis,
    add_activity_points
)

# 사용자 권한 조회
permissions = get_user_permissions(user)
print(f"최대 포트폴리오: {permissions['combined_permissions']['max_portfolios']}")

# 포트폴리오 생성 가능 여부 확인
can_create, message = can_create_portfolio(user, current_count=2)
if not can_create:
    raise HTTPException(status_code=403, detail=message)

# AI 분석 요청 가능 여부 확인
can_request, message = can_request_ai_analysis(user)
if not can_request:
    raise HTTPException(status_code=403, detail=message)

# 활동 점수 추가
add_activity_points(user, points=50, activity_type="포트폴리오 생성")
db.commit()
```

### JavaScript (Frontend)

```javascript
// 권한 조회
const response = await api.get('/auth/tier/permissions');
const permissions = response.data.permissions;

console.log(`VIP 등급: ${response.data.vip_tier}`);
console.log(`최대 포트폴리오: ${permissions.max_portfolios}`);
console.log(`고급 차트: ${permissions.advanced_charts ? '가능' : '불가능'}`);

// 등급 상태 조회
const statusResponse = await api.get('/auth/tier/status');
const status = statusResponse.data;

if (status.next_tier) {
  const progress = status.next_tier.progress_percentage;
  console.log(`다음 등급까지: ${progress}%`);
  console.log(`필요 점수: ${status.next_tier.remaining_activity_points}`);
}
```

## 🛠️ 권한 체크 유틸리티 함수

### 포트폴리오 생성 체크
```python
from app.utils.tier_permissions import can_create_portfolio

can_create, message = can_create_portfolio(user, current_portfolio_count=5)
if not can_create:
    # 권한 없음: "포트폴리오 생성 한도에 도달했습니다. (최대 5개, 현재 VIP 등급: SILVER)"
    raise HTTPException(status_code=403, detail=message)
```

### AI 분석 요청 체크
```python
from app.utils.tier_permissions import can_request_ai_analysis, increment_ai_requests

can_request, message = can_request_ai_analysis(user)
if not can_request:
    raise HTTPException(status_code=403, detail=message)

# AI 분석 실행
result = perform_ai_analysis(...)

# 사용량 증가
increment_ai_requests(user)
db.commit()
```

### 리포트 생성 체크
```python
from app.utils.tier_permissions import can_generate_report, increment_report_generation

can_generate, message = can_generate_report(user)
if not can_generate:
    raise HTTPException(status_code=403, detail=message)

# 리포트 생성
report = generate_report(...)

# 사용량 증가
increment_report_generation(user)
db.commit()
```

### 고급 기능 접근 체크
```python
from app.utils.tier_permissions import (
    can_access_advanced_charts,
    can_export_report,
    can_access_real_time_data
)

# 고급 차트 접근
can_access, message = can_access_advanced_charts(user)
if not can_access:
    # Starter 이상 플랜 필요
    raise HTTPException(status_code=403, detail=message)

# 리포트 내보내기
can_export, message = can_export_report(user)
if not can_export:
    # Starter 이상 플랜 필요
    raise HTTPException(status_code=403, detail=message)

# 실시간 데이터 접근
can_access_rt, message = can_access_real_time_data(user)
if not can_access_rt:
    # Pro 이상 플랜 필요
    raise HTTPException(status_code=403, detail=message)
```

## 📈 VIP 등급 자동 업데이트

VIP 등급은 활동 점수 또는 총 자산이 변경될 때마다 자동으로 업데이트됩니다.

```python
from app.utils.tier_permissions import update_vip_tier

# 방법 1: 활동 점수 추가 시 자동 업데이트
add_activity_points(user, points=50, activity_type="포트폴리오 생성")
# 내부적으로 update_vip_tier()가 호출되어 자동 업그레이드

# 방법 2: 수동 업데이트
new_tier, tier_changed = update_vip_tier(user)
if tier_changed:
    print(f"🎊 VIP 등급 상승! → {new_tier}")
```

## 🔄 월별 사용량 리셋

AI 요청 횟수와 리포트 생성 횟수는 매월 자동으로 리셋됩니다.

```python
from app.utils.tier_permissions import reset_monthly_usage_if_needed

# 사용자 정보 조회 시 자동으로 리셋 체크
reset_monthly_usage_if_needed(user)
db.commit()
```

마지막 리셋 시점부터 30일이 경과하면 자동으로 사용량이 0으로 리셋됩니다.

## ⚙️ 설정 및 커스터마이징

등급별 권한 설정은 `backend/app/utils/tier_permissions.py` 파일에서 수정할 수 있습니다.

```python
# VIP 등급별 권한
VIP_TIER_PERMISSIONS = {
    'bronze': {
        'max_portfolios': 3,
        'historical_data_months': 3,
        'activity_point_multiplier': 1.0,
    },
    # ...
}

# 멤버십 플랜별 권한
MEMBERSHIP_PERMISSIONS = {
    'free': {
        'monthly_ai_requests': 10,
        'monthly_reports': 2,
        'advanced_charts': False,
        # ...
    },
    # ...
}

# VIP 등급 업그레이드 기준
VIP_TIER_THRESHOLDS = {
    'silver': {'activity_points': 100, 'total_assets_만원': 5000},
    'gold': {'activity_points': 500, 'total_assets_만원': 10000},
    # ...
}
```

## 🚀 프로덕션 배포 시 주의사항

1. **테스트 엔드포인트 제거**
   - `/auth/tier/test-upgrade` 엔드포인트는 반드시 제거하거나 admin 권한으로 제한하세요.

2. **활동 점수 획득 로직 구현**
   - 실제 포트폴리오 생성, 진단 완료 등의 이벤트에 `add_activity_points()` 호출 추가

3. **멤버십 결제 시스템 연동**
   - 결제 완료 시 `membership_plan`, `membership_start_date`, `membership_end_date` 업데이트
   - 자동 갱신 또는 만료 처리 로직 구현

4. **권한 체크 적용**
   - 모든 주요 기능(포트폴리오, AI 분석, 리포트 등)에 권한 체크 추가

5. **데이터베이스 백업**
   - 등급 관련 필드가 추가되었으므로 마이그레이션 전 백업 필수

## 📞 문의

등급 체계 관련 문의사항이 있으시면 다음 채널을 이용해주세요:
- GitHub Issues: https://github.com/your-repo/issues
- 이메일: support@kingoportfolio.com
