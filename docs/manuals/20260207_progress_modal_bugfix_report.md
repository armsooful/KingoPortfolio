# ProgressModal 주식 데이터 적재 버그 수정 보고서

## 1. 개요

주식 데이터 적재 시 ProgressModal에서 발생한 3가지 버그를 분석하고 수정했습니다. 사용자의 요구사항(Phase 1/2 구분, 자동 종료 제거)을 구현한 후 발견된 실행 오류들입니다.

---

## 2. 발견된 버그 및 원인

### 2.1 버그 #1: Phase 2 진행 중 Phase 1 Badge 표시

**증상:**
```
상황: Phase 2 (데이터베이스 저장) 진행 중
표시: Phase 1 (데이터 수집) 배지가 활성화 (녹색)
```

**근본 원인:**

1. **Backend - Phase 전환 신호 누락**
   - `admin.py line 140`: Phase 1로 설정만 함
   - Phase 2로 전환하는 `set_phase("Phase 2")` 호출 없음

2. **Backend - Phase 2 로그 prefix 미포함**
   - `real_data_loader.py`: Phase 2 진행 콜백에서 ticker만 전달
   - 예: `progress_callback(idx, "005930", True)` ← "[Phase 2]" prefix 없음

3. **Frontend - Phase 판별 로직 실패**
   ```javascript
   // ProgressModal.jsx line 142-144
   const currentPhase = progress.phase ||
     (progress.current_item && progress.current_item.includes('[Phase 1]') ? 'Phase 1' : 'Phase 2');
   ```
   - `progress.phase`가 "Phase 2"로 설정되지 않음
   - `current_item`에 "[Phase 2]" prefix 없어 Phase 1로 인식

**영향:**
- Phase 2 진행 상황을 Phase 1로 오인
- 사용자가 진행 상황을 올바르게 이해할 수 없음

---

### 2.2 버그 #2: Success Count 누적 (5771 = 2886 + 2885)

**증상:**
```
Phase 1 완료: 2886건 수집 → success_count = 2886 증가
Phase 2 완료: 2885건 저장 → success_count = 2885 증가 (또 증가)
결과: 완료 메시지에서 5771건 표시 ❌
```

**근본 원인:**

1. **Progress Callback의 중복 카운팅**
   ```python
   # Phase 1: real_data_loader.py line 1123
   progress_callback(completed_count, f"[Phase 1] {ticker}", True, None)
   # → progress.success_count += 1 (2886번)

   # Phase 2: real_data_loader.py line 1150
   progress_callback(idx, f"[Phase 2] {ticker}", True, None)
   # → progress.success_count += 1 (2885번 또 증가)

   # 결과: 2886 + 2885 = 5771
   ```

2. **Success Count 리셋 미실행**
   - Phase 2 전환 시 `set_phase(..., reset_counts=True)` 미호출
   - Phase 1 카운트가 Phase 2 카운트에 누적됨

**영향:**
- 완료 메시지에서 부정확한 처리 건수 표시
- 실제 Phase 2 처리 건수 파악 불가

---

### 2.3 버그 #3: Progress Bar Total 불일치 (2885 vs 2886)

**증상:**
```
상단 진행률:      2885 / 2885 완료 ✓
하단 완료 메시지: 총 2886건 중 2886건 성공 ✗ (불일치)
```

**근본 원인:**

1. **초기 Total 설정 시점의 차이**
   ```python
   # admin.py: 초기 total 설정 (line 123-131)
   total_items = db.query(count(FdrStockListing)).filter(...).scalar()
   # 결과: 2885 (조회 시점의 레코드 개수)

   # real_data_loader.py: 실제 처리 (Phase 2 반복)
   for idx, listing in enumerate(listings, start=1):
       stats.total_records += 1
   # 결과: 2886 (실제 처리한 개수)
   ```

2. **Progress Total 동기화 미실행**
   - 초기 설정된 `progress.total = 2885`가 끝까지 유지됨
   - 실제 처리 건수 2886으로 업데이트되지 않음

**영향:**
- 상단 진행률과 하단 메시지의 수치 불일치
- 사용자 혼동

---

## 3. 수정 내역

### 3.1 수정 #1: Phase 2 감지 및 자동 전환 (Commit: 5211e2c)

**파일:** `backend/app/services/real_data_loader.py`

```python
# Phase 2 진행 로그에 "[Phase 2]" prefix 추가
# 수정 전:
progress_callback(idx, listing.ticker, True, None)

# 수정 후:
progress_callback(idx, f"[Phase 2] {listing.ticker}", True, None)
```

**파일:** `backend/app/routes/admin.py`

```python
# on_progress 함수에 Phase 2 자동 감지 로직 추가
def on_progress(current, ticker, success=None, error=None):
    # Phase 2 시작 감지: "[Phase 2]" prefix가 있으면 자동 전환
    if ticker and isinstance(ticker, str) and "[Phase 2]" in ticker:
        current_state = progress_tracker.get_progress(task_id)
        if current_state and current_state.get("phase") != "Phase 2":
            # Phase 2로 전환 및 success/failed count 초기화
            progress_tracker.set_phase(task_id, "Phase 2", reset_counts=True)

    progress_tracker.update_progress(...)
```

**효과:**
- ✅ Phase 2 로그에서 자동으로 phase 전환
- ✅ `set_phase(..., reset_counts=True)` 실행으로 카운트 초기화
- ✅ Frontend가 "[Phase 2]" prefix로 올바른 phase 판별

---

### 3.2 수정 #2: Success Count 리셋 (Commit: 5211e2c 포함)

**작동 원리:**

```python
# progress_tracker.py의 set_phase 메서드
def set_phase(self, task_id: str, phase: str, reset_counts: bool = False):
    if reset_counts:
        self._progress[task_id]["success_count"] = 0      # Phase 1 카운트 제거
        self._progress[task_id]["failed_count"] = 0
```

**결과:**
```
Phase 1 → Phase 2 전환:
  - Phase 1: success_count = 2886 (수집 완료, 디스플레이용)
  - set_phase() 호출: success_count = 0으로 리셋
  - Phase 2: success_count = 0 ~ 2886 (저장 진행)
  - 최종: success_count = 2886 (Phase 2만 카운트)
```

**효과:**
- ✅ 완료 메시지: "총 2886건 중 2886건 성공" (정확)
- ✅ Phase 1과 Phase 2 카운트 분리

---

### 3.3 수정 #3: Progress Total 동기화 (Commit: 39f5d8c)

**파일:** `backend/app/routes/admin.py`

```python
# 완료 메시지 전송 전 progress.total 동기화
progress = progress_tracker.get_progress(task_id)
if progress and progress.get("total") != result.total_records:
    # total 재조정: 초기 예상값(2885) → 실제값(2886)
    progress["total"] = result.total_records

progress_tracker.update_progress(
    task_id,
    current=result.total_records,
    current_item=f"완료: {result.success_records}건 성공, {result.failed_records}건 실패",
    success=True,
)
```

**효과:**
```
수정 전:  2885 / 2885 완료  (header)
        완료: 2886건 성공  (footer) ✗ 불일치

수정 후:  2886 / 2886 완료  (header)
        완료: 2886건 성공  (footer) ✓ 일치
```

---

## 4. 기술적 구현 세부사항

### 4.1 Phase 자동 감지 메커니즘

**상태 전이:**
```
Phase 1 (수집) → on_progress("[Phase 2] 005930", success=True)
    ↓
admin.py: "[Phase 2]" 감지
    ↓
progress_tracker.set_phase("Phase 2", reset_counts=True)
    ↓
success_count = 0으로 리셋
    ↓
Phase 2 (저장) 시작
```

### 4.2 Count 관리

| 단계 | success_count | 설명 |
|------|---------------|------|
| Phase 1 시작 | 0 | 초기 상태 |
| Phase 1 진행 | 2886 | 2886개 콜백 호출 |
| Phase 1→2 전환 | 0 | `reset_counts=True` 실행 |
| Phase 2 진행 | 0~2886 | 각 항목마다 +1 |
| 완료 | 2886 | Phase 2 최종 값 |

### 4.3 Frontend Phase 판별 로직

```javascript
// ProgressModal.jsx line 142-144
const currentPhase = progress.phase ||
  (progress.current_item?.includes('[Phase 1]') ? 'Phase 1' : 'Phase 2');
const isPhase1 = progress.status === 'running' && currentPhase === 'Phase 1';
```

**작동:**
1. `progress.phase = "Phase 2"` (backend에서 설정)
2. OR `current_item.includes('[Phase 2]')` (prefix 매칭)
3. → 올바른 badge 표시

---

## 5. 검증 결과

### 5.1 E2E 테스트 (2886개 주식 실제 적재)

✅ **Phase 1 단계**
- Badge: "Phase 1: 수집" (녹색)
- 실시간 로그: "[Phase 1] 307870 데이터 수집 완료"
- 스피너 + 진행 메시지

✅ **Phase 2 단계**
- Badge 전환: "Phase 2: 저장" (파란색)
- 진행률: 0% → 100%
- 최종 완료: "총 2886건 중 2886건 성공"

✅ **수치 일치**
- 상단 진행률: 2886 / 2886 ✓
- 중간 통계: 성공 2886 ✓
- 하단 메시지: 2886건 ✓

---

## 6. 커밋 이력

| 커밋 해시 | 제목 | 버그 |
|----------|------|------|
| `5211e2c` | Fix ProgressModal Phase detection and success count | #1, #2 |
| `39f5d8c` | Fix progress bar total mismatch | #3 |

---

## 7. 결론

### 수정 전 문제점
- Phase 2 진행 중 Phase 1 표시
- Success count 누적 (5771건)
- Header/Footer 수치 불일치 (2885 vs 2886)

### 수정 후 개선사항
- ✅ 올바른 phase 인식 및 badge 전환
- ✅ 정확한 success count (2886건)
- ✅ 완벽한 수치 일치

### 설계 원칙
1. **Backend-driven Phase 관리**: Backend에서 phase 신호를 명시적으로 보냄
2. **Automatic Count Reset**: Phase 전환 시 자동으로 카운트 초기화
3. **Progress Synchronization**: 완료 시점에 모든 수치를 동기화

이를 통해 사용자는 정확한 진행 상황을 실시간으로 파악할 수 있습니다.
