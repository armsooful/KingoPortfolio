# Foresto Compass UX 개선 보고서

> 작성일: 2026-02-13
> 대상: Foresto Compass v1.0 (KingoPortfolio)
> 목적: 현재 UX 문제점 분석 및 "첨단 AI 투자 학습 플랫폼" 이미지에 맞는 개선 방향 수립

---

## 1. 감사 범위

분석 대상 페이지 6개, CSS 파일 32개를 전수 조사했다.

| 페이지 | 경로 | 주요 역할 |
|--------|------|----------|
| Landing | `/` | 서비스 소개, 회원가입 유도 |
| Login | `/login` | 로그인 |
| Dashboard | `/dashboard` | 시장 현황, 뉴스, 관심 종목 |
| Screener | `/screener` | Compass Score 기반 종목 탐색 |
| Survey | `/survey` | 투자 성향 진단 설문 |
| Stock Detail | `/admin/stock-detail` | 개별 종목 상세 분석 |

---

## 2. 현황 문제점 분석

### 2-1. 디자인 시스템 부재 — 페이지별 파편화

현재 페이지마다 완전히 다른 시각 언어를 사용하여, 동일 서비스라는 인식이 어렵다.

| 페이지 | 배경 | 카드 스타일 | 전체 인상 |
|--------|------|-----------|----------|
| Dashboard | `#667eea → #764ba2` 보라 그라데이션 전체 | 반투명 글래스모피즘 시도 | 화려하지만 과한 보라색 |
| Screener | `#f5f5f5` 밝은 회색 | 흰색 border 카드 | 관리자 도구 느낌 |
| Survey | `#f5f5f5` 밝은 회색 | 노란색 경고 박스 (`#fff3cd`) | 2010년대 관공서 사이트 |
| Landing | `#667eea → #764ba2` 보라 그라데이션 전체 | 흰색 카드 with box-shadow | 별도 마케팅 페이지 |
| Login | `#ffffff` 순백 | 단순 카드 with 파란 버튼 | 기본 Bootstrap 템플릿 |
| Stock Detail | `#f8f9fa` 연한 회색 | `#f8f9fa` 배경 패널 | 개발자 대시보드 |

**진단**: 통합 디자인 토큰(색상, 간격, 그림자, 라운드) 시스템이 없다. `:root` CSS 변수가 선언되어 있으나(`App.css:11-24`) 대부분의 페이지 CSS에서 이를 무시하고 하드코딩된 값을 사용한다.

### 2-2. 컬러 팔레트 — 보라색 단일 의존

```css
/* 현재 시스템 전역에서 반복 사용되는 단일 그라데이션 */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

이 그라데이션이 사용되는 곳:
- 헤더 (`App.css:64`)
- 대시보드 배경 (`MarketDashboard.css:5`)
- 랜딩 페이지 배경 (`LandingPage.css:4`)
- AI 요약 카드 (`MarketDashboard.css:58`)
- CTA 버튼 (`MarketDashboard.css:575`)
- 설문 시작 버튼

**문제점**:
- 보라+분홍 조합은 엔터테인먼트/축제 분위기를 연상시킴
- 금융/AI 플랫폼의 신뢰감과 거리가 있음
- 단일 그라데이션의 과도한 반복으로 시각적 피로감 유발
- 배경과 CTA 버튼이 같은 색이라 버튼의 시각적 구분력이 약함

### 2-3. 아이콘 & 로고 — 시스템 이모지 의존

현재 전체 서비스에서 시스템 이모지를 아이콘으로 사용한다.

| 위치 | 사용 이모지 | 문제 |
|------|-----------|------|
| 로고 | 🌲 | 기기/OS마다 렌더링 다름, 브랜드 아이덴티티 없음 |
| 대시보드 섹션 | 📈 📊 🎯 📰 ❄️ 🔥 | 전문 서비스 이미지 저하 |
| 사용자 등급 | 🥉 BRONZE, 🆓 FREE | 게임 UI 느낌 |
| 신호등 | 🟢 🟡 🔴 | 기기별 크기/색상 불일치 |
| 랜딩 피처 | 📊 💼 📈 🎯 📰 📉 | 유치한 인상 |

**진단**: SVG 커스텀 아이콘이 단 하나도 없다. 이모지는 접근성(스크린리더 해석 불일치), 일관성(OS별 렌더링 차이), 전문성 측면에서 모두 부적합하다.

### 2-4. 타이포그래피 — 기본 시스템 폰트

```css
/* App.css:28-30 — 시스템 기본 폰트 스택만 사용 */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto',
  'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans',
  'Helvetica Neue', sans-serif;
```

**문제점**:
- 한글 전용 폰트 미설정 — macOS에서는 Apple SD Gothic Neo, Windows에서는 맑은 고딕 등 OS 기본 폰트로 렌더링
- 숫자/금융 데이터용 모노스페이스 폰트 미설정 (`.stock-ticker`에만 `monospace` 지정)
- 폰트 크기 체계 불일치: 대시보드 헤더 `2.5rem`, 스크리너 헤더 `1.5rem` (같은 h1 레벨)
- 시세 표시에 `font-variant-numeric: tabular-nums` 적용이 일부만 됨

### 2-5. 데이터 시각화 — 숫자 나열에 그침

"AI 기반 분석 플랫폼"을 표방하지만 실제 데이터 표현은 텍스트 중심이다.

| 데이터 | 현재 표현 | 경쟁사 표현 |
|--------|----------|-----------|
| Compass Score | `100.0` 텍스트 뱃지 (초록 테두리) | 원형 게이지 + 등급 아이콘 (AlphaSquare) |
| 4개 카테고리 점수 | 텍스트 나열 | 레이더/스파이더 차트 (Quantus) |
| 주요 지수 | 숫자 + 등락률 텍스트 | 스파크라인 + 미니 캔들차트 (TradingView) |
| 상승/하락 종목 | 리스트 텍스트 | 히트맵 + 버블차트 (StockMatrix) |
| 종목 시계열 | 외부 차트 (Chart.js) | 인라인 스파크라인 + 인터랙티브 차트 |

**진단**: Chart.js가 이미 설치되어 있으나 대시보드/스크리너 핵심 UI에서 활용되지 않고 있다. Compass Score라는 고유 점수 체계가 있음에도 시각적 임팩트가 없다.

### 2-6. 인터랙션 & 애니메이션 — 정적 페이지

| 요소 | 현재 | 업계 표준 |
|------|------|----------|
| 로딩 상태 | `"불러오는 중..."` 텍스트 | 스켈레톤 UI (회색 펄스 블록) |
| 페이지 전환 | 즉시 교체 (깜빡임) | fade-in/slide-up 트랜지션 |
| 숫자 변경 | 즉시 교체 | 카운트업/카운트다운 애니메이션 |
| 호버 효과 | `translateY(-2px)` | 미묘한 그림자/스케일 + 배경 변화 |
| 스크롤 | 없음 | Intersection Observer 기반 reveal |
| 토스트/알림 | `alert()` | 슬라이드 인 토스트 컴포넌트 |

**진단**: `@keyframes fadeIn`이 대시보드 요약 카드에만 적용되어 있다. 나머지 페이지는 완전히 정적이다. 사용자 액션(필터 변경, 정렬, 페이지 전환)에 대한 시각 피드백이 부족하다.

### 2-7. 네비게이션 — 드롭다운 5개 과밀

현재 상단 네비게이션:
```
[🌲 Foresto Compass] [학습▾] [진단▾] [포트폴리오▾] [계정▾] [관리▾]  [이름/등급] [로그아웃]
```

**문제점**:
- 5개 드롭다운이 한 줄에 배치 — 인지 부하 높음
- 각 드롭다운에 3~6개 하위 항목 — 전체 메뉴 항목 20개 이상
- 모바일에서 햄버거 메뉴 → 전체 목록 펼침 → 스크롤 필요
- `관리` 메뉴가 일반 사용자에게도 보이는지 불명확 (권한 분리 이슈)

### 2-8. 폼 & 입력 요소 — 네이티브 HTML 그대로

| 요소 | 현재 | 문제 |
|------|------|------|
| `<select>` 드롭다운 | 네이티브 브라우저 스타일 | OS마다 다르게 보임, 검색 불가 |
| 검색 입력 | 기본 `<input>` | 아이콘 없음, 자동완성 UI 약함 |
| 페이지네이션 | `[이전] 1/144 [다음]` | 숫자 페이지 선택 불가, 점프 불가 |
| 체크박스 | 네이티브 `<input type="checkbox">` | 커스텀 스타일 없음 |
| 버튼 | 여러 스타일 혼재 | `.btn-survey`, `.btn-cta`, `.btn-retry` 등 통일되지 않은 버튼 클래스 |

### 2-9. 반응형 — 최소한의 대응

```css
/* MarketDashboard.css 반응형: 단순 1컬럼 전환만 */
@media (max-width: 768px) {
  .indices-grid { grid-template-columns: 1fr; }
  .stocks-section { grid-template-columns: 1fr; } /* 2→1 */
}
```

**문제점**:
- 테이블(Screener)의 모바일 대응 없음 — 12컬럼이 그대로 가로 스크롤
- 모바일 전용 패턴(바텀 네비게이션, 풀스크린 모달, 스와이프 제스처) 없음
- 터치 타겟 크기 미검증 (별표 버튼 `padding: 2px 4px` — 너무 작음)

### 2-10. 접근성 (Accessibility)

- `<table>` 헤더에 `scope` 속성 없음
- 색상만으로 정보 전달 (상승=빨강, 하락=파랑 — 색각 이상 사용자 고려 없음)
- 이모지에 `aria-label` 없음
- 키보드 네비게이션 미검증

---

## 3. 개선 방향: "Bloomberg Terminal meets AI"

### 3-1. 디자인 원칙 수립

1. **다크 퍼스트 (Dark-first)**: 금융 데이터는 어두운 배경에서 가독성이 높다
2. **데이터 밀도 (Data Density)**: 한 화면에 더 많은 정보를, 정돈된 형태로
3. **시각적 계층 (Visual Hierarchy)**: 중요한 숫자 → 보조 지표 → 메타 정보 순
4. **일관성 (Consistency)**: 모든 페이지가 동일한 디자인 토큰을 공유
5. **최소 장식 (Minimal Chrome)**: 그라데이션/그림자 최소화, 데이터가 주인공

### 3-2. 컬러 시스템 리디자인

#### 다크 테마 팔레트

```css
:root {
  /* 배경 계층 */
  --bg-base:       #0b0e14;     /* 최하위 배경 (거의 검정) */
  --bg-surface:    #131620;     /* 카드/패널 배경 */
  --bg-elevated:   #1a1f2e;     /* 모달, 드롭다운 배경 */
  --bg-hover:      #242938;     /* 호버 상태 */

  /* 테두리 */
  --border-subtle:  #1e2330;    /* 기본 구분선 */
  --border-default: #2a3040;    /* 카드 테두리 */

  /* 텍스트 */
  --text-primary:   #e2e8f0;    /* 주요 텍스트 */
  --text-secondary: #8892a4;    /* 보조 텍스트 */
  --text-muted:     #505a6e;    /* 비활성 텍스트 */

  /* 브랜드 액센트 */
  --accent-primary:   #00d4aa;  /* 시안/그린 — AI/테크 느낌 */
  --accent-secondary: #6366f1;  /* 인디고 — 보조 액센트 */
  --accent-tertiary:  #f59e0b;  /* 앰버 — 경고/하이라이트 */

  /* 시맨틱 */
  --color-up:     #ef4444;      /* 상승 (한국 증시 관례) */
  --color-down:   #3b82f6;      /* 하락 */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-danger:  #ef4444;

  /* 등급 색상 */
  --grade-s:  #fbbf24;          /* S — 골드 */
  --grade-a:  #22c55e;          /* A+, A — 그린 */
  --grade-b:  #3b82f6;          /* B+, B — 블루 */
  --grade-c:  #f97316;          /* C+, C — 오렌지 */
  --grade-d:  #ef4444;          /* D — 레드 */
  --grade-f:  #6b7280;          /* F — 그레이 */
}
```

#### 라이트 테마 (선택 제공)

```css
[data-theme="light"] {
  --bg-base:       #f8fafc;
  --bg-surface:    #ffffff;
  --bg-elevated:   #ffffff;
  --bg-hover:      #f1f5f9;
  --border-subtle:  #e2e8f0;
  --border-default: #cbd5e1;
  --text-primary:   #0f172a;
  --text-secondary: #64748b;
  --text-muted:     #94a3b8;
}
```

### 3-3. 타이포그래피 시스템

```css
/* 한글 본문: Pretendard (가변 폰트, 무료, CDN 제공) */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css');

/* 숫자/코드: JetBrains Mono (무료, 금융 데이터 최적) */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

:root {
  --font-sans:  'Pretendard Variable', 'Pretendard', -apple-system, sans-serif;
  --font-mono:  'JetBrains Mono', 'SF Mono', monospace;

  /* 크기 스케일 (rem 기반) */
  --text-xs:    0.75rem;    /* 12px — 면책조항, 메타 */
  --text-sm:    0.8125rem;  /* 13px — 보조 정보 */
  --text-base:  0.875rem;   /* 14px — 본문 기본 */
  --text-lg:    1rem;       /* 16px — 강조 본문 */
  --text-xl:    1.25rem;    /* 20px — 섹션 제목 */
  --text-2xl:   1.5rem;     /* 24px — 페이지 제목 */
  --text-3xl:   2rem;       /* 32px — 히어로 숫자 */
}

/* 금융 숫자 전용 클래스 */
.num-display {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
```

### 3-4. 아이콘 시스템 — Lucide Icons

**선택 이유**: React 컴포넌트 지원, 트리쉐이킹 가능, 800+ 아이콘, MIT 라이선스, 1.5KB/아이콘.

```bash
npm install lucide-react
```

교체 매핑:

| 현재 이모지 | Lucide 아이콘 | 용도 |
|------------|--------------|------|
| 🌲 | `<TreePine />` → 커스텀 SVG 로고 | 브랜드 |
| 📈 | `<TrendingUp />` | 상승/시장 |
| 📊 | `<BarChart3 />` | 분석/차트 |
| 🎯 | `<Target />` | 진단/목표 |
| 📰 | `<Newspaper />` | 뉴스 |
| 🔥 | `<Flame />` | 상승 종목 |
| ❄️ | `<Snowflake />` | 하락 종목 |
| ⭐/☆ | `<Star />` / `<StarOff />` | 관심 종목 |
| 🟢🟡🔴 | 커스텀 SVG 신호등 | 시장 상태 |
| 🥉🆓 | `<Award />` / `<Badge />` | 사용자 등급 |

### 3-5. 데이터 시각화 강화

#### A. Compass Score 게이지 (핵심 시각물)

```
현재:  [100.0]  S    (텍스트 뱃지)

개선:  ╭───────────╮
       │  ◉ 68.8  │  B+   ← 도넛형 게이지, 색상으로 등급 표현
       │  ███████░░│       ← 진행 바 + 수치
       ╰───────────╯
```

- Chart.js `Doughnut` 컴포넌트로 원형 게이지 구현
- 중앙에 점수 + 등급 텍스트
- 색상은 등급별 `--grade-*` 변수 연동

#### B. 4개 카테고리 레이더 차트

```
현재:  재무 70.5 | 밸류 85.0 | 기술 60.2 | 리스크 55.3  (텍스트)

개선:      재무
           ╱ ╲
      리스크    밸류     ← Chart.js Radar
           ╲ ╱
           기술
```

- Stock Detail 페이지의 Compass 섹션에 Radar 차트 추가
- 호버 시 각 축 점수 툴팁 표시

#### C. 지수 스파크라인

```
현재:  KOSPI  5,507.01  -15.26 (-0.28%)   (숫자만)

개선:  KOSPI  5,507.01  ~~~╲  -0.28%       ← 7일 미니 라인차트
```

- Chart.js `Line` (옵션: `pointRadius: 0`, `borderWidth: 1.5`)
- 높이 32px의 인라인 미니 차트

#### D. 스크리너 히트맵 뷰 (토글)

```
현재:  [테이블 뷰만]

개선:  [테이블 뷰] [히트맵 뷰]  ← 토글 버튼

       히트맵: 사각형 크기 = 시가총액, 색상 = Compass Score
       ┌──────────┬─────┬────┐
       │ 삼성전자  │ LG  │현대│
       │  68.8 B+ │72 A │ .. │
       └──────────┴─────┴────┘
```

### 3-6. 인터랙션 & 애니메이션

#### A. 스켈레톤 로딩 (Skeleton UI)

```css
.skeleton {
  background: linear-gradient(90deg,
    var(--bg-surface) 25%,
    var(--bg-elevated) 50%,
    var(--bg-surface) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

적용 위치: 스크리너 테이블 로딩, 대시보드 지수 카드 로딩, 종목 상세 데이터 로딩

#### B. 숫자 카운트업 (Count-up Animation)

```jsx
// 점수, 지수, 가격 표시 시 0 → 목표값 애니메이션
// 라이브러리: react-countup (2KB gzip)
import CountUp from 'react-countup';

<CountUp end={68.8} decimals={1} duration={0.8} />
```

#### C. 페이지 트랜지션

```jsx
// framer-motion 활용
import { motion } from 'framer-motion';

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.25 } },
  exit:    { opacity: 0, y: -8, transition: { duration: 0.15 } },
};
```

#### D. 마이크로 인터랙션

| 상호작용 | 현재 | 개선 |
|---------|------|------|
| 관심 종목 토글 | 별표 색 변경 | 별 아이콘 스케일 바운스 + 색상 전환 |
| 테이블 행 호버 | 배경 `#f9fafb` | 왼쪽 `accent-primary` 보더 + 배경 변화 |
| 필터 변경 | 즉시 리로드 | 테이블 fade-out → 스켈레톤 → fade-in |
| 정렬 토글 | 화살표 문자 `▼▲` | SVG 아이콘 회전 애니메이션 |
| 등급 뱃지 | 정적 텍스트 | 처음 나타날 때 살짝 스케일업 |

### 3-7. 레이아웃 통합

#### A. 통일 레이아웃 쉘

```
┌──────────────────────────────────────────┐
│ [로고]  [검색]        [알림] [프로필]      │ ← 슬림 헤더 (56px)
├──────────────────────────────────────────┤
│ Sidebar │           메인 콘텐츠           │ ← 선택적 사이드바
│ ------  │  ┌─────────────────────────┐   │
│ 대시보드 │  │     페이지 콘텐츠        │   │
│ 스크리너 │  │                         │   │
│ 관심종목 │  │                         │   │
│ 진단    │  └─────────────────────────┘   │
│ 학습    │                                │
├──────────────────────────────────────────┤
│ Footer (면책조항)                          │
└──────────────────────────────────────────┘
```

- 모든 페이지가 동일한 `--bg-base` 배경
- 콘텐츠는 `--bg-surface` 카드 안에 배치
- 페이지별로 다른 배경색/그라데이션 완전 폐지
- 사이드바는 데스크톱에서 축소 가능 (아이콘만 표시)

#### B. 모바일 레이아웃

```
┌──────────────┐
│ [로고] [검색] │ ← 모바일 헤더
├──────────────┤
│              │
│  메인 콘텐츠  │ ← 풀 너비
│              │
├──────────────┤
│ 🏠 📊 ⭐ 👤  │ ← 바텀 탭 네비게이션 (고정)
└──────────────┘
```

바텀 탭 구성: 홈(대시보드) | 스크리너 | 관심종목 | 프로필/더보기

### 3-8. 컴포넌트 현대화

| 현재 | 개선안 | 비고 |
|------|--------|------|
| 네이티브 `<select>` | 커스텀 드롭다운 (검색 가능) | Headless UI 또는 Radix 활용 |
| 기본 `<input>` | 아이콘 + 클리어 버튼 포함 검색 바 | 돋보기 아이콘, X 클리어 |
| HTML `<table>` | 가상 스크롤 테이블 | `@tanstack/react-virtual` |
| `[이전] 1/144 [다음]` | 숫자 페이지네이션 + 점프 | `1 2 3 ... 142 143 144` |
| `alert()` | 토스트 알림 | `react-hot-toast` (3KB) |
| 노란 경고 박스 | 글래스 배너 with dismiss | 닫기 버튼 + 로컬 스토리지 기억 |

### 3-9. 모바일 최적화

| 항목 | 현재 | 개선 |
|------|------|------|
| 네비게이션 | 햄버거 → 전체 목록 | 바텀 탭 (4항목) |
| 테이블 | 가로 스크롤 (12컬럼) | 카드 리스트 뷰 전환 |
| 터치 타겟 | `2px 4px` (별표) | 최소 44x44px |
| 스와이프 | 없음 | 관심 종목 스와이프 삭제 |
| 검색 | 인라인 input | 풀스크린 검색 모달 |

### 3-10. 접근성 (Accessibility)

- 모든 아이콘에 `aria-label` 추가
- 색상 외 추가 구분자 제공 (상승 `▲` + 빨강, 하락 `▼` + 파랑)
- `<table>` 헤더에 `scope="col"` 추가
- 키보드 네비게이션: Tab으로 테이블 행 이동, Enter로 상세 진입
- 최소 색상 대비 4.5:1 준수 (WCAG AA)

---

## 4. 벤치마크 비교

### 4-1. 국내 경쟁사 UX 특징

| 서비스 | 테마 | 핵심 시각물 | 차별점 |
|--------|------|-----------|--------|
| AlphaSquare | 다크 | 점수 게이지 + AI 요약 카드 | 카드 기반 레이아웃 |
| StockMatrix | 라이트 | 30개 지표 히트맵 | 정보 밀도 최고 |
| Quantus | 다크 | 레이더 차트 + 백테스트 그래프 | 퀀트 전문가 타겟 |
| IntelliQuant | 라이트/다크 토글 | AI 자연어 리포트 | 리포트 중심 |
| 증권플러스 | 라이트 | 실시간 호가창 | 트레이딩 중심 |

### 4-2. 해외 벤치마크

| 서비스 | 참고 요소 |
|--------|----------|
| TradingView | 다크 테마, 미니 차트, 스파크라인 |
| Bloomberg Terminal | 정보 밀도, 다크 배경, 모노스페이스 숫자 |
| Robinhood | 미니멀 UI, 카운트업 애니메이션, 원형 차트 |
| Finviz | 히트맵 뷰, 필터 UI |

### 4-3. Foresto Compass 포지셔닝

```
                  정보 밀도 높음
                      │
         StockMatrix  │  Bloomberg
                      │
     ─────────────────┼─────────────────
     초보 친화적       │       전문가 대상
                      │
         Robinhood    │  TradingView
           ▲          │
     Foresto Compass  │  Quantus
     (목표 포지션)     │
                      │
                  정보 밀도 낮음
```

**목표 포지셔닝**: "교육 목적 + 적정 정보 밀도 + AI 인사이트" — Robinhood의 접근성과 Bloomberg의 신뢰감 사이.

---

## 5. 구현 우선순위 로드맵

### Phase 1: 기반 (Foundation) — 체감 변화 최대

| # | 작업 | 난이도 | 체감 효과 | 예상 작업량 |
|---|------|--------|----------|-----------|
| 1 | CSS 변수 기반 다크 테마 전환 | 중 | 극대 | 2~3일 |
| 2 | Pretendard + JetBrains Mono 폰트 적용 | 하 | 높음 | 0.5일 |
| 3 | 이모지 → Lucide SVG 아이콘 전면 교체 | 중 | 높음 | 1~2일 |
| 4 | 커스텀 SVG 로고 적용 | 하 | 중간 | 0.5일 |

### Phase 2: 시각화 (Visualization) — 핵심 차별화

| # | 작업 | 난이도 | 체감 효과 | 예상 작업량 |
|---|------|--------|----------|-----------|
| 5 | Compass Score 원형 게이지 컴포넌트 | 중 | 극대 | 1일 |
| 6 | 4개 카테고리 레이더 차트 | 중 | 높음 | 1일 |
| 7 | 지수 카드 스파크라인 | 중 | 높음 | 1일 |
| 8 | 스켈레톤 로딩 컴포넌트 | 하 | 중간 | 0.5일 |

### Phase 3: 인터랙션 (Interaction) — 완성도

| # | 작업 | 난이도 | 체감 효과 | 예상 작업량 |
|---|------|--------|----------|-----------|
| 9 | 숫자 카운트업 애니메이션 | 하 | 중간 | 0.5일 |
| 10 | 페이지 트랜지션 (framer-motion) | 중 | 중간 | 1일 |
| 11 | 커스텀 드롭다운 / 검색 컴포넌트 | 중 | 높음 | 1~2일 |
| 12 | 토스트 알림 시스템 | 하 | 중간 | 0.5일 |

### Phase 4: 모바일 & 접근성

| # | 작업 | 난이도 | 체감 효과 | 예상 작업량 |
|---|------|--------|----------|-----------|
| 13 | 바텀 탭 네비게이션 (모바일) | 중 | 높음 | 1일 |
| 14 | 스크리너 카드 리스트 뷰 (모바일) | 중 | 높음 | 1일 |
| 15 | 접근성 (aria, 키보드, 대비) | 중 | - | 1일 |
| 16 | 라이트/다크 테마 토글 | 중 | 중간 | 1일 |

**총 예상 작업량**: 약 15~18일 (풀타임 기준)

---

## 6. 기술 스택 추가 사항

현재 설치 필요한 패키지:

```bash
npm install lucide-react           # SVG 아이콘 (트리쉐이킹 지원)
npm install framer-motion          # 페이지 트랜지션, 마이크로 애니메이션
npm install react-countup          # 숫자 카운트업 (2KB)
npm install react-hot-toast        # 토스트 알림 (3KB)
```

이미 설치된 활용 가능 패키지:
- `chart.js` + `react-chartjs-2` → Doughnut(게이지), Radar, Line(스파크라인)
- `tailwindcss` → 유틸리티 클래스 기반 빠른 스타일링

---

## 7. Before / After 기대 효과

```
Before (현재)                          After (개선 후)
━━━━━━━━━━━━━━━━━━━━━━━              ━━━━━━━━━━━━━━━━━━━━━━━
보라색 그라데이션 배경                   다크 테마 + 시안 액센트
시스템 이모지 아이콘                     Lucide SVG 아이콘
"100.0" 텍스트 뱃지                     원형 게이지 + 레이더 차트
숫자만 나열한 테이블                     스파크라인 + 히트맵 뷰
"불러오는 중..." 텍스트                  스켈레톤 펄스 로딩
네이티브 select 드롭다운                 커스텀 검색 가능 드롭다운
alert() 팝업                           슬라이드 토스트
보라 그라데이션 → 즉시 화면              fade-in 페이지 트랜지션
OS 기본 한글 폰트                       Pretendard 가변 폰트
상단 드롭다운 5개 (모바일 복잡)           바텀 탭 네비게이션

전체 인상:                              전체 인상:
"2018년 스타트업 MVP"                   "Bloomberg meets AI 학습 도구"
```

---

## 8. 참고 자료

- [Pretendard 폰트](https://github.com/orioncactus/pretendard)
- [Lucide Icons](https://lucide.dev/)
- [Radix UI Primitives](https://www.radix-ui.com/)
- [Framer Motion](https://www.framer.com/motion/)
- [Chart.js Doughnut/Radar](https://www.chartjs.org/docs/)
- [TradingView UI 패턴 분석](https://www.tradingview.com/)

---

> 본 보고서는 현재 Foresto Compass v1.0의 UX 상태를 진단하고, "첨단 AI 투자 학습 플랫폼" 이미지에 맞는 개선 방향을 제시한다. 실제 구현 시 Phase 1(기반)부터 순차 적용을 권장하며, 각 Phase 완료 후 사용자 피드백을 반영하여 다음 Phase를 조정한다.
