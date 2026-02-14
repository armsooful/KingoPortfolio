# UI 테마 시스템 & 스타일 가이드

> 이 문서는 Foresto Compass의 글로벌 테마 시스템 규칙과 CSS 작성 가이드를 정리한 것입니다.
> 기존 페이지 검증, 새 페이지/컴포넌트 작성 시 반드시 참조하세요.

---

## 1. 테마 시스템 개요

- **테마 파일**: `frontend/src/styles/theme.css`
- **방식**: CSS Custom Properties (`:root` = 라이트, `[data-theme="dark"]` = 다크)
- **토글 훅**: `frontend/src/hooks/useTheme.js` → `document.documentElement.setAttribute('data-theme', theme)`
- **진입점**: `frontend/src/index.css`에서 `@import './styles/theme.css'`

---

## 2. CSS 변수 매핑표 (반드시 준수)

### 배경

| 용도 | 올바른 변수 | 라이트 값 | 다크 값 | 잘못된 예시 (사용 금지) |
|------|-----------|----------|--------|----------------------|
| 페이지 배경 | `var(--bg)` | `#f0f2f7` | `#0f1117` | `#f5f5f5`, `#f8f9fa`, `background: white` |
| 카드/섹션 배경 | `var(--card)` | `#ffffff` | `#1a1d2e` | `--card-bg`, `--card-background`, `white` |
| 카드 내부/인풋 배경 | `var(--card-inner)` | `#fafbfc` | `#161928` | `--input-bg`, `--table-header-bg`, `#f9f9f9`, `#f5f5f5` |
| 호버 상태 | `var(--card-hover)` | `#f8f9ff` | `#1e2235` | `--row-hover`, `--table-row-hover`, `#f3f4f6` |

### 텍스트

| 용도 | 올바른 변수 | 라이트 값 | 다크 값 | 잘못된 예시 |
|------|-----------|----------|--------|-----------|
| 기본 텍스트 | `var(--text)` | `#1f2937` | `#e5e7eb` | `--text-primary`, `#333`, `#111827`, `color: black` |
| 보조 텍스트 | `var(--text-secondary)` | `#6b7280` | `#9ca3af` | `#666`, `#555`, `#374151` |
| 뮤트 텍스트 | `var(--text-muted)` | `#9ca3af` | `#6b7280` | `#888`, `#999`, `#aaa` |

### 보더 & 그림자

| 용도 | 올바른 변수 | 잘못된 예시 |
|------|-----------|-----------|
| 기본 보더 | `var(--border)` | `--border-color`, `#e0e0e0`, `#d1d5db`, `#ddd`, `#eee` |
| 연한 보더 | `var(--border-light)` | `#f3f4f6` 하드코딩 |
| 그림자 (소) | `var(--shadow-sm)` | `box-shadow: 0 2px 8px rgba(0,0,0,0.1)` |
| 그림자 (중) | `var(--shadow-md)` | `box-shadow: 0 4px 15px rgba(0,0,0,0.15)` |
| 그림자 (대) | `var(--shadow-lg)` | `box-shadow: 0 10px 30px rgba(0,0,0,0.2)` |

### 브랜드 & 특수

| 용도 | 올바른 변수 | 값 |
|------|-----------|---|
| 주 브랜드색 | `var(--primary)` | `#667eea` |
| 브랜드 어두운 | `var(--primary-dark)` | `#5568d3` |
| 브랜드 밝은 | `var(--primary-light)` | `#8b9cf7` |
| 악센트 | `var(--accent)` | `#764ba2` |
| 둥근 모서리 | `var(--radius)` | `12px` |
| 주식 상승 | `var(--stock-up)` | `#e53935` / `#ff6b6b` |
| 주식 하락 | `var(--stock-down)` | `#1e88e5` / `#64b5f6` |

---

## 3. 페이지 레이아웃 표준 패턴

### 3-1. 페이지 컨테이너

```css
.{page}-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}
```

- 보라색 그라데이션 배경 **사용 금지** (`background: linear-gradient(135deg, #667eea, #764ba2)`)
- 페이지 배경은 `var(--bg)`로 body에서 자동 적용됨

### 3-2. 페이지 헤더

```css
.{page}-header {
  margin-bottom: 1.5rem;
}

.{page}-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  color: var(--text, #1f2937);
}

.{page}-subtitle {
  color: var(--text-secondary, #6b7280);
  font-size: 0.875rem;
  margin: 0;
}
```

- 센터 정렬 + 흰색 텍스트 스타일 **사용 금지** (구 스타일)
- 좌측 정렬, `var(--text)` 사용

### 3-3. 카드/섹션

```css
.{page}-section {
  background: var(--card, #ffffff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--radius, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  margin-bottom: 1.5rem;
}

.{page}-section h2 {
  color: var(--text, #1f2937);
  margin-bottom: 1.25rem;
  font-size: 1.15rem;
  font-weight: 700;
}
```

### 3-4. 내부 카드 (카드 안의 카드)

```css
.{page}-inner-card {
  background: var(--card-inner, #fafbfc);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--radius, 12px);
  padding: 1.25rem;
}
```

### 3-5. 테이블

```css
.{page}-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.{page}-table thead th {
  background: var(--card-inner, #f9fafb);
  padding: 0.6rem 0.5rem;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
  border-bottom: 2px solid var(--border, #e5e7eb);
  color: var(--text-secondary, #374151);
}

.{page}-table tbody td {
  padding: 0.5rem;
  border-bottom: 1px solid var(--border-light, #f3f4f6);
  color: var(--text, #111827);
}

.{page}-table tbody tr:hover {
  background: var(--card-hover, #f9fafb);
}
```

### 3-6. 폼 입력 (input, select)

```css
.{page}-input,
.{page}-select {
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  font-size: 0.875rem;
  background: var(--card-inner, #fafbfc);
  color: var(--text, #1f2937);
  transition: border-color 0.2s;
}

.{page}-input:focus,
.{page}-select:focus {
  outline: none;
  border-color: var(--primary, #667eea);
}
```

### 3-7. CTA / 주요 버튼

```css
.btn-primary-action {
  background: linear-gradient(135deg, var(--primary, #667eea), var(--accent, #764ba2));
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
}
```

- 그라데이션 버튼은 `var(--primary)` → `var(--accent)` 사용
- 보조 버튼은 `var(--card-inner)` 배경 + `var(--border)` 보더

### 3-8. 빈 상태 (Empty State)

```css
.{page}-empty {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-secondary, #6b7280);
  background: var(--card, #ffffff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--radius, 12px);
}
```

### 3-9. 로딩 스피너

```css
.{page}-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border, #e5e7eb);
  border-top-color: var(--primary, #667eea);
  border-radius: 50%;
  animation: {page}-spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}
```

- 흰색 스피너 **사용 금지** (다크모드에서 안 보임)
- `var(--border)` 바탕 + `var(--primary)` 강조

### 3-10. 에러 메시지

```css
.{page}-error {
  background: #fef2f2;
  border-left: 4px solid #ef4444;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

[data-theme="dark"] .{page}-error {
  background: rgba(239, 68, 68, 0.1);
}

.{page}-error p {
  margin: 0;
  color: #ef4444;
  font-size: 0.875rem;
}
```

### 3-11. 면책 문구 (Disclaimer)

```css
/* 글로벌 컴포넌트 — App.css에 정의됨 */
.disclaimer-box {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 4px solid #f59e0b;
  border-radius: var(--radius);
}

.disclaimer-title { color: #f59e0b; }
.disclaimer-list { color: var(--text-secondary); }
```

- `<Disclaimer type="..." />` 컴포넌트 사용
- 인라인 스타일 **사용 금지** — CSS 클래스(`disclaimer-box`) 사용

### 3-12. 반응형 브레이크포인트

```css
@media (max-width: 768px) {
  .{page}-page { padding: 1.5rem 0.75rem; }
  .{page}-header h1 { font-size: 1.25rem; }
  /* 그리드: 1fr로 축소 */
}
```

---

## 4. CSS 클래스명 충돌 방지 규칙

### 문제 사례

여러 CSS 파일에서 동일 클래스명을 정의하면 로드 순서에 따라 예상치 못한 오버라이드 발생.

| 충돌 클래스 | 문제 발생 파일 | 해결 방법 |
|-----------|-------------|---------|
| `.cta-card` | PortfolioRecommendation.css → MarketDashboard에 영향 | `.portfolio-cta .cta-card`로 스코프 지정 |
| `.section-title` | Backtest.css `color: #333` → 대시보드 제목 덮어씀 | `var(--text, #333)`으로 변경 |
| `.ai-disclaimer` | InvestmentReport.css → 대시보드에 영향 | `.investment-report .ai-disclaimer`로 스코프 지정 |
| `.info-section` | Backtest/Scenario 공통 사용 | `.scenario-page .info-section`으로 스코프 지정 |
| `.spinner` | App.css ↔ Backtest.css ↔ Scenario.css 충돌 | `.scenario-spinner`, `.backtest-spinner` 등 접두사 |
| `.error-message` | App.css ↔ Scenario.css 충돌 | `.scenario-error` 등 접두사 |

### 규칙

1. **페이지 전용 클래스**: 반드시 `{page}-` 접두사 사용 (`.screener-table`, `.watchlist-row`)
2. **공통 클래스 덮어쓸 때**: 부모 스코프 지정 (`.scenario-page .info-section`)
3. **글로벌 유틸리티 클래스**: `App.css`에만 정의 (`.btn`, `.error-message`, `.disclaimer-box`)
4. **절대 금지**: 스코프 없는 일반 클래스에 하드코딩 색상 넣기

---

## 5. 다크모드 전용 오버라이드가 필요한 경우

대부분 CSS 변수만으로 자동 전환되지만, 아래 경우 `[data-theme="dark"]` 선택자가 필요:

```css
/* 1. 반투명 배경이 필요한 에러/경고 */
[data-theme="dark"] .{page}-error {
  background: rgba(239, 68, 68, 0.1);
}

/* 2. 고정 색상 보더가 테마별로 달라야 할 때 */
[data-theme="dark"] .risk-card {
  border-color: #7f1d1d;  /* 라이트: #fca5a5 */
}
```

- CSS 변수로 처리 가능하면 `[data-theme="dark"]` 사용 **최소화**
- `var(--변수, 폴백값)` 패턴으로 대부분 해결 가능

---

## 6. 인라인 스타일 규칙

### 허용

- 동적으로 계산되는 값 (차트 너비, 프로그레스 바 %)
- 시나리오 카드 선택 시 `borderColor` (동적 색상)

### 금지

- 하드코딩 배경색/텍스트색 (`style={{ background: 'white' }}`)
- 고정 레이아웃 값 (padding, margin, fontSize 등)
- Disclaimer 등 공용 컴포넌트의 스타일

---

## 7. 적용 완료 페이지 / 미적용 페이지

### 적용 완료

| 페이지 | CSS 파일 | 상태 |
|--------|---------|------|
| 대시보드 | `MarketDashboard.css` | theme.css 변수 전면 적용 |
| 종목 스크리너 | `StockScreener.css` | 전체 리라이트 완료 |
| 관심 종목 | `Watchlist.css` | 전체 리라이트 완료 |
| 시나리오 모의실험 | `ScenarioSimulation.css` | 전체 리라이트 완료 |
| 헤더 | `App.css` (header 섹션) | CSS 변수 적용 완료 |
| 푸터 | `Footer.css` | CSS 변수 적용 완료 |
| Disclaimer 컴포넌트 | `App.css` (disclaimer 섹션) | 인라인→CSS 클래스 전환 완료 |

### 검증 필요 (하드코딩 색상 잔존 가능)

| 페이지 | CSS 파일 | 주요 확인 포인트 |
|--------|---------|---------------|
| 백테스트 | `Backtest.css` | 보라색 그라데이션 배경, `white` 카드, `#333` 텍스트 |
| 포트폴리오 추천 | `PortfolioRecommendation.css` | 카드 배경, 폼 스타일 |
| 투자 리포트 | `InvestmentReport.css` | 대량 하드코딩 색상 |
| 설문 조사 | `App.css` (survey 섹션) | `white` 카드, `#333`, `#666` 텍스트 |
| 진단 결과 | `App.css` (result 섹션) | `white` 카드, `#f8f9fa` 배경 |
| 진단 히스토리 | `App.css` (history 섹션) | `white` 배경, `#ddd` 보더 |
| 로그인/회원가입 | `App.css` (auth 섹션) | `white` 카드 |
| 프로필 | `Profile.css` | 확인 필요 |
| 관리 페이지 | `DataManagement.css` | 확인 필요 |
| 종목 상세 | `StockDetail.css` | 확인 필요 |
| 용어 학습 | `Terminology.css` | 확인 필요 |

---

## 8. 새 페이지 작성 체크리스트

- [ ] 페이지 컨테이너: `max-width: 1200px`, 보라색 배경 없음
- [ ] 헤더: 좌측 정렬, `var(--text)` + `var(--text-secondary)`
- [ ] 모든 카드/섹션: `var(--card)` 배경 + `var(--border)` + `var(--shadow-sm)`
- [ ] 모든 텍스트: `var(--text)`, `var(--text-secondary)`, `var(--text-muted)` 중 택1
- [ ] 모든 보더: `var(--border)` 또는 `var(--border-light)`
- [ ] 폼 입력: `var(--card-inner)` 배경 + `var(--border)` + `var(--text)`
- [ ] 테이블 헤더: `var(--card-inner)` 배경
- [ ] 테이블 행 호버: `var(--card-hover)`
- [ ] 스피너: `{page}-spinner` 접두사, `var(--border)` + `var(--primary)`
- [ ] 에러: `{page}-error` 접두사, 다크모드 `rgba()` 오버라이드
- [ ] 면책 문구: `<Disclaimer type="..." />` 컴포넌트 사용
- [ ] CTA 버튼: `var(--primary)` → `var(--accent)` 그라데이션
- [ ] 반응형: 768px 브레이크포인트
- [ ] 클래스명: `{page}-` 접두사로 충돌 방지
- [ ] 하드코딩 색상: `#333`, `#666`, `white`, `#e0e0e0` 등 **0개** 확인
- [ ] 다크모드 토글로 라이트/다크 모두 시각 검증
