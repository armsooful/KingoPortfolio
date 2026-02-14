# Foresto Compass UI/UX 개선 방향 보고서

> 작성일: 2026-02-14
> 참고 자료: 반응형 투자 대시보드 디자인 사례 분석 (Flowworks, DevITCloud, Modern Dashboard 등)

---

## 1. 현재 상태 분석

### 1.1 전체 구조

| 항목 | 현재 상태 | 문제점 |
|------|----------|--------|
| CSS 방식 | 페이지별 개별 CSS 파일 33개 + App.css(글로벌) | 일관성 부족, 중복 코드 다수 |
| Tailwind | v4 설치됨, `@import "tailwindcss"` 선언됨 | 실사용 거의 없음 — 전체 CSS가 수동 작성 |
| 반응형 | `@media (max-width: 768px)` 기본 대응 | 태블릿(1024px) 구간 미흡, 터치 최적화 부재 |
| 디자인 시스템 | `:root` CSS 변수 일부 사용 | 체계적 토큰(spacing, typography, radius) 부재 |
| 컴포넌트 | 12개 공유 컴포넌트 | 페이지별 인라인 스타일 및 중복 UI 다수 |
| 차트 | Chart.js (react-chartjs-2) | StockDetailPage에서만 사용, 대시보드 미적용 |

### 1.2 페이지별 현황

| 페이지 | 레이아웃 | 모바일 대응 | 차트/시각화 | 상태 |
|--------|---------|------------|-----------|------|
| LandingPage | Hero + Feature Grid + Steps | 기본 대응 | 없음 (일러스트 카드만) | 양호 |
| MarketDashboard | 지수 Grid → 상승/하락 → 관심종목 → 뉴스 → CTA | 768px 기본 대응 | 없음 (숫자만) | **개선 필요** |
| StockScreener | 필터 패널 + 테이블 | 가로 스크롤 | 없음 | **개선 필요** |
| StockDetail | 티커 검색 → 차트 + 지표 + AI코멘터리 | 미흡 | Chart.js Line/Bar | 양호 |
| WatchlistPage | 목록 + 알림 토글 | 기본 대응 | 없음 | 보통 |
| ProfilePage | 폼 + 구독 관리 + 동의 이력 | 기본 대응 | 없음 | 양호 |
| SurveyPage | 단계형 설문 | 양호 | 없음 | 양호 |
| DiagnosisResult | 결과 카드 + 포트폴리오 그리드 | 기본 대응 | 없음 | 보통 |
| PortfolioBuilder | 다단계 구성 | 기본 대응 | Chart.js | 보통 |
| BacktestPage | 파라미터 → 결과 차트 | 미흡 | Chart.js | 보통 |
| ScenarioSimulation | 슬라이더 + 결과 | 미흡 | Chart.js | 보통 |

### 1.3 핵심 문제 요약

1. **대시보드에 차트/시각화 부재**: MarketDashboard는 핵심 랜딩 페이지인데 차트 없이 숫자 텍스트만 나열
2. **Tailwind 미활용**: 설치만 되어 있고 실사용이 없어, 모든 CSS가 수동 — 유지보수 비용 높음
3. **디자인 토큰 비체계적**: 색상은 `#667eea` 하드코딩, spacing은 `rem` 값이 페이지마다 다름
4. **모바일 터치 UX 부재**: 스와이프, 풀투리프레시, 바텀시트 등 모바일 네이티브 패턴 없음
5. **로딩 UX 단일**: 전체 페이지 스피너만 사용, 스켈레톤 UI 미적용
6. **다크모드 미지원**: 투자 앱 사용자층의 야간 사용 빈도가 높음에도 불구

---

## 2. 참고 사례 분석 — 적용 가능 패턴

### 2.1 투자 앱 대시보드 핵심 패턴

| 패턴 | 설명 | 적용 우선순위 |
|------|------|-------------|
| **KPI 카드 상단 배치** | 핵심 지표(지수, Compass Score 평균 등)를 카드 그리드로 최상단 배치 | 높음 |
| **미니 차트 in 카드** | 지수 카드에 7일 미니 라인 차트(sparkline) 삽입 | 높음 |
| **반응형 카드 그리드** | `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))` | 높음 |
| **시계열 차트 기간 선택** | 1일/1주/1개월/3개월/1년 탭으로 차트 기간 전환 | 중간 |
| **종목 카드 → 상세 슬라이드** | 종목 클릭 시 오른쪽 패널(또는 바텀시트)에서 상세 표시 | 중간 |
| **스켈레톤 로딩** | 데이터 로딩 시 카드 형태의 회색 플레이스홀더 | 높음 |
| **다크모드** | 투자 앱 사용자의 야간 사용 빈도 고려 | 낮음(후순위) |

### 2.2 반응형 breakpoint 전략

참고 사례에서 공통적으로 사용하는 3단계 breakpoint:

```
Mobile:  < 640px   → 1열, 카드 스택, 바텀 내비게이션
Tablet:  640-1024px → 2열 그리드, 축약 사이드바
Desktop: > 1024px  → 4열 KPI + 2열 차트 + 사이드바
```

현재 Foresto의 breakpoint(`768px`, `1024px`)는 유사하나, **640px 이하 모바일 최적화가 부족**함.

### 2.3 Flowworks 카드 그리드 패턴 (참고)

- 각 KPI 카드에 미니 차트(sparkline) + 변동률 배지
- 카드 hover 시 상세 수치 표시
- 그리드 간격: `gap: 1rem`으로 모바일에서도 가독성 유지
- 카드 내부: 타이틀(13px) → 값(24px bold) → 변동(14px 컬러) → 미니차트(48px 높이)

---

## 3. 구현 방향 — 단계별 로드맵

### Phase 1: 디자인 시스템 기반 구축 (기반 작업)

**목표**: 일관된 디자인 토큰과 공유 컴포넌트로 기반 마련

**3.1.1 디자인 토큰 정의**

```css
:root {
  /* Colors */
  --color-primary: #667eea;
  --color-primary-dark: #5568d3;
  --color-accent: #764ba2;
  --color-success: #16a34a;
  --color-danger: #dc2626;
  --color-warning: #f59e0b;

  /* 한국 주식 컬러 (국제표준 반대) */
  --color-stock-up: #e53935;     /* 상승 = 빨강 */
  --color-stock-down: #1e88e5;   /* 하락 = 파랑 */

  /* Spacing scale */
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */

  /* Typography */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
}
```

**3.1.2 공유 컴포넌트 추가**

| 컴포넌트 | 용도 | 사용처 |
|---------|------|--------|
| `<KPICard>` | 핵심 지표 카드 (값 + 변동 + sparkline) | Dashboard, StockDetail |
| `<Skeleton>` | 스켈레톤 로딩 플레이스홀더 | 모든 페이지 |
| `<MiniChart>` | 48px 높이 sparkline (Chart.js 또는 SVG) | KPICard, 관심종목 |
| `<Badge>` | 등급/상태 배지 (A+, 상승, 구독중 등) | Screener, Watchlist, Dashboard |
| `<EmptyState>` | 빈 데이터 상태 (아이콘 + 메시지 + CTA) | 통합 |

**수정 파일**: `frontend/src/components/` 에 신규 파일 추가, `App.css` 디자인 토큰 추가

---

### Phase 2: MarketDashboard 리디자인 (최우선)

**목표**: 텍스트 나열 → 시각적 대시보드로 전환

**현재 구조:**
```
Header → AI 시장 요약 → 지수(숫자만) → 상승/하락(리스트) → 관심종목 → 뉴스 → CTA
```

**목표 구조:**
```
[KPI 카드 그리드 — 4열]
  KOSPI 2,650 +0.5% [sparkline]  |  KOSDAQ 870 -0.3% [sparkline]
  S&P500 5,200 +0.8% [sparkline] |  NASDAQ 16,400 +1.2% [sparkline]

[AI 시장 요약 — 신호등 + 텍스트]

[2열 레이아웃]
  [상승 종목 Top 5 — 가로 바 차트]  |  [하락 종목 Top 5 — 가로 바 차트]

[관심 종목 — Compass Score 미니 카드]
  삼성전자 72점 B [4축 미니바] | 카카오 58점 C [4축 미니바] | ...

[시장 뉴스 — 타임라인 형식]

[CTA — 3열 → 모바일 1열]
```

**핵심 변경사항:**

| 항목 | 현재 | 변경 |
|------|------|------|
| 지수 표시 | `index-card`에 숫자만 | KPICard + 7일 sparkline |
| 상승/하락 종목 | 텍스트 리스트 | 가로 바 차트 (등락률 시각화) |
| 관심 종목 | 단순 리스트 | Compass Score 미니 카드 (4축 바 포함) |
| 레이아웃 | 단일 열 | 2열 (데스크톱) / 1열 (모바일) |
| 로딩 | 전체 스피너 | 섹션별 스켈레톤 |

**모바일 대응 (< 640px):**
- KPI 카드: 4열 → 2열 그리드 (2x2)
- 상승/하락: 2열 → 1열 스택
- 관심 종목: 가로 스크롤 카드
- 뉴스: 카드 축약 (제목 + 소스만)

**수정 파일**: `MarketDashboardPage.jsx`, `MarketDashboard.css`

---

### Phase 3: StockScreener 반응형 강화

**목표**: 넓은 테이블 → 모바일 친화적 카드/리스트

**현재 문제:**
- 12열 테이블이 모바일에서 가로 스크롤 발생
- 필터 패널이 한 줄에 4개 select → 모바일에서 깨짐

**변경 방향:**

| 뷰포트 | 레이아웃 |
|--------|---------|
| Desktop (>1024px) | 현재 테이블 유지 (12열) |
| Tablet (640-1024px) | 축약 테이블 (종목명, Score, 등급, 시가총액만) |
| Mobile (<640px) | **카드 레이아웃** 전환 — 각 종목이 카드 1장 |

**모바일 카드 디자인:**
```
┌─────────────────────────────┐
│ ★ 삼성전자         005930   │
│   KOSPI · 반도체             │
│                              │
│  [72점 B+]   52,300원       │
│  ├ 재무 78 ████████░░       │
│  ├ 밸류 62 ██████░░░░       │
│  ├ 기술 75 ████████░░       │
│  └ 리스크 68 ███████░░░     │
│                              │
│  PER 12.5 · PBR 1.2 · 2.1% │
└─────────────────────────────┘
```

**필터 패널:**
- 모바일: 접이식 필터 (기본 숨김, "필터" 버튼으로 토글)
- 정렬: 바텀시트 또는 드롭다운

**수정 파일**: `StockScreenerPage.jsx`, `StockScreener.css`

---

### Phase 4: 관심 종목(Watchlist) + 종목 상세(StockDetail) 개선

**4.1 WatchlistPage:**
- 현재: 단순 리스트
- 변경: Compass Score 요약 카드 (4축 미니바 + 등급 배지 + sparkline)
- 추가: 전체 평균 Score 표시, 업종 분산 파이차트

**4.2 StockDetailPage:**
- 현재: 이미 Chart.js 적용, 구조 양호
- 변경:
  - 모바일 차트 높이 최적화 (200px → `aspectRatio: 1.5`)
  - 탭 네비게이션 (가격차트 | 기술지표 | 재무분석 | AI코멘터리)
  - Compass Score 4축 레이더 차트 추가

**수정 파일**: `WatchlistPage.jsx`, `Watchlist.css`, `StockDetailPage.jsx`, `StockDetail.css`

---

### Phase 5: Header/Navigation 개선

**현재 문제:**
- 데스크톱 네비게이션: 그룹 5개(학습, 진단, 포트폴리오, 계정, 관리) — 항목이 많아 복잡
- 모바일: 전체 드로어 — 스크롤 필요
- `user-info` 영역이 이메일 + VIP + 멤버십 모두 표시 → 복잡

**변경 방향:**
- 데스크톱: 메인 메뉴 3개(학습, 분석, 포트폴리오) + 더보기 드롭다운
- 모바일: 바텀 탭 네비게이션 (학습/스크리너/관심/포트폴리오/더보기) — 투자 앱 표준 패턴
- 사용자 영역: 아바타 아이콘 + 클릭 시 프로필 드롭다운

**수정 파일**: `Header.jsx`, `App.css`

---

### Phase 6: 성능 및 UX 미세 조정

| 항목 | 구현 내용 |
|------|----------|
| 스켈레톤 로딩 | 모든 API 호출 페이지에 `<Skeleton>` 적용 |
| 풀투리프레시 | 모바일 대시보드에서 아래로 당기면 데이터 새로고침 |
| 무한 스크롤 | Screener 페이지네이션 → Intersection Observer 무한 스크롤 |
| 토스트 알림 | 관심종목 추가/삭제 시 하단 토스트 (현재: alert 사용) |
| 애니메이션 | 숫자 카운트 업, 카드 진입 fade-in (framer-motion 또는 CSS) |

---

## 4. Tailwind 활용 전략

### 현재 상황
- `tailwindcss@4.1.18` 설치됨
- `@tailwindcss/vite` 플러그인 설정됨
- `tailwind.config.js`에 브랜드 컬러 정의됨
- **하지만 실제 JSX에서 Tailwind 클래스 사용 없음** — 모든 스타일이 CSS 파일

### 점진적 전환 전략

**기존 CSS 파일을 한꺼번에 바꾸지 않는다.** 새로 만들거나 리디자인하는 컴포넌트부터 Tailwind 사용.

| 단계 | 대상 | 방식 |
|------|------|------|
| 1 | 신규 공유 컴포넌트 (KPICard, Skeleton, Badge 등) | Tailwind 클래스 직접 사용 |
| 2 | MarketDashboard 리디자인 시 | Tailwind 클래스로 새로 작성 |
| 3 | StockScreener 모바일 카드 뷰 | Tailwind 클래스 |
| 4+ | 기존 페이지는 그대로 유지 | 필요 시 점진적 마이그레이션 |

**Tailwind 사용 규칙:**
- 디자인 토큰(색상, spacing)은 `tailwind.config.js`에서 관리
- 반복 패턴은 `@apply`로 유틸리티 클래스 생성 (`.btn-primary`, `.card` 등)
- 기존 CSS 파일의 강제 마이그레이션은 하지 않음

---

## 5. 우선순위 및 구현 순서

```
Phase 1 (디자인 시스템)  ← 모든 Phase의 기반
   ↓
Phase 2 (MarketDashboard) ← 사용자가 가장 많이 보는 페이지
   ↓
Phase 3 (StockScreener)  ← 두 번째로 중요한 페이지
   ↓
Phase 4 (Watchlist + StockDetail) ← 기존 기반 위에 개선
   ↓
Phase 5 (Header/Navigation) ← 전체 UX 흐름 개선
   ↓
Phase 6 (성능/미세 조정)  ← 마무리
```

### 예상 수정 파일 목록

| Phase | 수정/신규 파일 | 변경 유형 |
|-------|--------------|----------|
| 1 | `App.css` (디자인 토큰 추가) | 수정 |
| 1 | `tailwind.config.js` (토큰 확장) | 수정 |
| 1 | `components/KPICard.jsx` | 신규 |
| 1 | `components/Skeleton.jsx` | 신규 |
| 1 | `components/MiniChart.jsx` | 신규 |
| 1 | `components/Badge.jsx` | 신규 |
| 2 | `pages/MarketDashboardPage.jsx` | 대규모 수정 |
| 2 | `styles/MarketDashboard.css` | 대규모 수정 |
| 3 | `pages/StockScreenerPage.jsx` | 수정 (모바일 카드 추가) |
| 3 | `styles/StockScreener.css` | 수정 (반응형 추가) |
| 4 | `pages/WatchlistPage.jsx`, `StockDetailPage.jsx` | 수정 |
| 4 | `styles/Watchlist.css`, `StockDetail.css` | 수정 |
| 5 | `components/Header.jsx` | 대규모 수정 |
| 5 | `App.css` (header 섹션) | 수정 |

---

## 6. 제약 사항 및 고려 사항

### 6.1 기술적 제약
- **Chart.js 번들 크기**: 이미 사용 중이므로 sparkline도 Chart.js로 통일 (추가 라이브러리 X)
- **Tailwind v4**: CSS-first 설정 방식, `@import "tailwindcss"` 이미 적용됨
- **React 18**: Concurrent features 활용 가능 (Suspense 등), 하지만 현재 미사용

### 6.2 성능 제약 (MacBook 8GB RAM)
- 한 번에 1개 Phase만 진행
- 대규모 CSS 리팩터링 지양 — 신규 코드 위주로 Tailwind 적용
- 이미지/아이콘은 SVG 인라인 또는 이모지 유지 (아이콘 라이브러리 추가 지양)

### 6.3 호환성
- 지원 브라우저: Chrome 90+, Safari 14+, Firefox 90+ (한국 시장 특성상 Chrome 위주)
- iOS Safari: `position: sticky`, `backdrop-filter` 호환 확인 필요
- `dvh` (dynamic viewport height) 사용 시 iOS 15+ 필요

---

## 7. 결론

Foresto Compass의 현재 UI는 **기능은 충분하나 시각적 밀도가 부족**합니다. 투자 학습 플랫폼으로서:

1. **대시보드에 차트가 없다** — 가장 시급한 문제. KPI 카드 + sparkline만 추가해도 체감 품질이 크게 향상됨
2. **모바일 UX가 미흡** — 투자 앱 사용자의 60%+ 가 모바일. 바텀 탭, 카드 레이아웃, 스와이프 필수
3. **Tailwind 자산이 낭비** — 이미 설치·설정 완료. 신규 컴포넌트부터 활용하면 개발 속도 2배 향상

**권장 착수 순서**: Phase 1 (디자인 토큰 + 공유 컴포넌트) → Phase 2 (Dashboard 리디자인)

Phase 1은 신규 파일 4-5개 추가 + App.css 소폭 수정으로 완료 가능하며, Phase 2에서 Dashboard를 리디자인할 때 바로 활용할 수 있습니다.
