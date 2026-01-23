# Phase A 적용 체크리스트 & 구현 가이드
최초작성일자: 2026-01-17
최종수정일자: 2026-01-18

## (A-1 설명 자동 생성 로직의 실제 적용 절차)

작성일: 2026-01-17  
대상: 백엔드/데이터/프론트 개발자, 운영/법무 리뷰 담당

---

## 0. 목적과 원칙

### 목적
Phase A(설명 자동 생성)를 **실데이터(Phase 3-C) 연동 전에** 안정적으로 적용하여,
- 설명 결과의 **일관성**
- 규제 리스크 **최소화**
- 이후 실데이터 연동 시 **재작업 방지**
를 달성한다.

### 원칙 (불변)
- 추천/자문/최적화/판단 유도 금지
- 점수(Score)는 **내부용**이며 외부 노출 금지
- 데이터 소스가 바뀌어도 **설명 로직은 변경하지 않음**
- 결과가 흔들리면 Phase 3-C(입력)를 고치고 Phase A는 고정

---

## 1. Phase A 적용 범위

### 포함 (IN)
- 지표 입력 → 상태 분류(Rule) → 내부 스코어(선택) → 문구 템플릿 매핑 → 설명 출력
- 설명 길이/톤 제어 파라미터
- 금지 키워드 가드(자동 검사)

### 제외 (OUT)
- 종목 추천
- 비중 제안
- 매수/매도 타이밍 암시
- 실거래/주문 연동

---

## 2. 적용 단계 로드맵 (A 선적용 → C 연동)

### Step A-0. 기준선 고정 (필수)
- [ ] 템플릿 라이브러리 버전 태깅 (예: templates_v1)
- [ ] 금지 표현 리스트 버전 태깅 (예: banned_words_v1)
- [ ] 샘플 리포트(B-3) 1건을 “정답(Golden)”으로 지정

산출물
- templates_v1.md
- banned_words_v1.txt
- golden_report_sample.json (지표 입력/예상 출력 포함)

---

### Step A-1. 지표 입력 스키마 확정 (인터페이스)
아래 입력 스키마는 Phase 3-C가 어떤 소스를 쓰든 동일해야 한다.

- [ ] portfolio_id (string)
- [ ] start_date, end_date (YYYY-MM-DD)
- [ ] metrics
  - [ ] cagr (float, 예: 0.062)
  - [ ] volatility (float, 연율화 기준 명시)
  - [ ] mdd (float, 예: -0.18)
  - [ ] total_return (float, 예: 0.24)
  - [ ] period_days (int)
  - [ ] rebalance_enabled (bool)

추가 권장
- [ ] benchmark 비교 결과(선택): bench_total_return, bench_volatility 등

완료 기준
- [ ] 입력값 단위/정밀도(소수점 자리) 명시
- [ ] 연율화 기준(252 trading days 등) 명시

---

### Step A-2. 상태 분류 Rule 구현 (Deterministic)
Rule은 반드시 **결정적(deterministic)** 이어야 하며, 랜덤/LLM 의존을 금지한다.

- [ ] CAGR 상태: low/medium/high
- [ ] Volatility 상태: low/medium/high
- [ ] MDD 상태: stable/caution/large

권장 구현 방식
- 상수 테이블(Threshold) + 순수 함수(classifier)
- 설정 파일로 Threshold를 분리하되, 운영 변경은 버전 관리

완료 기준
- [ ] 동일 입력 → 동일 상태(항상)
- [ ] 경계값 테스트 케이스 통과

---

### Step A-3. 내부 스코어 계산 (옵션, 비노출)
- [ ] stability_score (0~100)
- [ ] growth_score (0~100)

주의
- 외부 응답/화면/리포트에 스코어 원값 노출 금지
- 스코어는 문구 선택의 “보정 값”으로만 사용

완료 기준
- [ ] API 응답에 score 필드가 없다
- [ ] 로그에는 남기되 개인정보/민감정보 최소화

---

### Step A-4. 문구 템플릿 매핑 (Template Resolver)
상태 조합으로 템플릿을 선택한다.

예)
- CAGR=medium, VOL=low, MDD=stable
  → 성격: “완만하지만 안정적”
  → 문구: summary_sentence_12

- [ ] 매핑 테이블 작성 (상태 조합 → template_id list)
- [ ] 랜덤 선택 금지(초기). 우선순위 기반(첫 번째) 선택 권장
- [ ] long/normal/short 길이 파라미터로 문구 세트 차등 출력

완료 기준
- [ ] 모든 상태 조합 커버(누락 0)
- [ ] template_id 미존재 시 fallback 정의 (예: neutral_default)

---

### Step A-5. 금지 키워드/문구 가드 (Regulatory Guard)
API 응답/리포트 생성 전에 텍스트를 검사한다.

- [ ] 금지 키워드 리스트(banned_words_v1) 적용
- [ ] 금지 패턴(정규식) 적용: “~해야”, “반드시”, “최적”, “추천” 등
- [ ] 위반 시 처리 정책
  - (권장) 템플릿 fallback + 경고 로그
  - (금지) 사용자에게 “위반” 메시지 노출(UX 악화)

완료 기준
- [ ] 위반 0건 또는 fallback으로 자동 치환됨
- [ ] CI에서 정적 검사로 위반 텍스트 검출

---

### Step A-6. Golden Test (샘플 리포트 1:1 재현)
B-3에서 완성한 샘플 리포트를 기준으로 자동 생성 결과가 동일해야 한다.

- [ ] golden 입력(지표) 준비
- [ ] expected 출력(JSON/텍스트) 준비
- [ ] 비교 기준
  - 문장 단위 동일(권장)
  - 혹은 template_id 동일 + 문장 유사도 허용(차선)

완료 기준
- [ ] CI에서 golden test 통과
- [ ] 릴리즈마다 동일 결과 재현

---

## 3. 구현 체크리스트 (개발자용)

### 백엔드
- [ ] classifier 모듈 분리 (pure function)
- [ ] template_resolver 모듈 분리
- [ ] guard 모듈 분리
- [ ] /analysis/explain API에서 위 3모듈을 순서대로 호출
- [ ] 템플릿/금지어 버전 파라미터 지원(기본값 v1)

### 프론트엔드
- [ ] “설명은 판단이 아님” 고지 유지
- [ ] 길이 파라미터(short/normal/long) 선택 UI는 옵션(초기엔 고정 가능)
- [ ] 문구가 fallback 되었을 때 UX 깨짐 없도록 레이아웃 안정화

### 데이터/운영
- [ ] 템플릿 변경은 PR + 리뷰 + 버전업으로만 반영
- [ ] 로그에 template_id와 상태 조합 기록(디버깅용)
- [ ] 배포 후 “금지어 위반률”, “fallback 비율” 모니터링

---

## 4. 운영·법무 점검 포인트 (필수)

- [ ] “추천/자문 아님” 고지 문구가 화면/리포트에 유지되는가
- [ ] 성과 보장/미래 예측 표현이 존재하지 않는가
- [ ] 비교 문구가 우열/서열로 읽히지 않는가
- [ ] 사용자가 결과를 “지시”로 오인할 소지가 없는가

---

## 5. Definition of Done (Phase A 적용 완료 기준)

- [ ] Rule 기반 상태 분류가 결정적으로 동작
- [ ] Template 매핑 누락 0
- [ ] 금지 키워드 위반 0 또는 자동 치환
- [ ] Golden Test 통과
- [ ] 배포 후 모니터링 지표(위반률/치환률/오류율) 준비

---

## 6. 다음 단계로의 연결 (Phase 3-C 적용 준비)

Phase A가 완료되면 Phase 3-C는 다음 원칙을 따른다.

- Phase 3-C는 **Phase A 입력 스키마**에 맞춘 정규화 값을 공급한다
- 결과가 달라지면 Phase 3-C(수익률/조정/결측 처리)를 수정한다
- Phase A는 고정한다
