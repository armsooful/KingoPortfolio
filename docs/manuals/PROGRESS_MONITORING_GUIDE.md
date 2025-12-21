# 📊 데이터 수집 진행 상황 모니터링 가이드

## ✅ 구현 완료!

데이터 수집 중 실시간 진행 상황을 모니터링할 수 있는 기능이 추가되었습니다.

## 🎯 주요 기능

### 1. 실시간 진행률 표시
- 현재 처리 중인 종목 표시
- 진행률 퍼센티지 (0-100%)
- 성공/실패 개수 실시간 업데이트

### 2. 시각적 프로그레스 바
- 파란색 그라데이션 프로그레스 바
- 퍼센티지 표시
- 완료 시 상태 변경

### 3. 자동 폴링 시스템
- 1초마다 진행 상황 자동 업데이트
- 완료 시 자동으로 폴링 중지
- 데이터 현황 자동 새로고침

## 🏗️ 아키텍처

```
┌─────────────────┐
│  프론트엔드      │
│  AdminPage      │
│  + ProgressBar  │
└────────┬────────┘
         │ HTTP Polling (1초마다)
         ↓
┌─────────────────┐
│   백엔드 API    │
│  /admin/progress│
│  /{task_id}     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ ProgressTracker │
│  (In-Memory)    │
│  - task_id      │
│  - current      │
│  - total        │
│  - success      │
│  - failed       │
└─────────────────┘
```

## 📝 추가된 파일

### 백엔드 (3개 파일)

1. **[backend/app/progress_tracker.py](backend/app/progress_tracker.py)** (NEW)
   - 진행 상황 추적 클래스
   - 스레드 안전한 상태 관리
   - 전역 인스턴스 제공

2. **[backend/app/services/data_loader.py](backend/app/services/data_loader.py)** (MODIFIED)
   - `load_korean_stocks()` 함수에 `task_id` 파라미터 추가
   - 진행 상황 추적 코드 추가
   - 각 종목 처리 시 진행률 업데이트

3. **[backend/app/routes/admin.py](backend/app/routes/admin.py)** (MODIFIED)
   - `GET /admin/progress/{task_id}` - 특정 작업 진행 상황
   - `GET /admin/progress` - 모든 작업 진행 상황
   - `DELETE /admin/progress/{task_id}` - 진행 상황 제거
   - `/load-stocks` 엔드포인트에서 task_id 반환

### 프론트엔드 (3개 파일)

1. **[frontend/src/components/ProgressBar.jsx](frontend/src/components/ProgressBar.jsx)** (NEW)
   - 진행률 표시 컴포넌트
   - 1초마다 자동 폴링
   - 완료 시 콜백 호출

2. **[frontend/src/services/api.js](frontend/src/services/api.js)** (MODIFIED)
   - `getProgress(taskId)` - 진행 상황 조회
   - `getAllProgress()` - 모든 진행 상황 조회

3. **[frontend/src/pages/AdminPage.jsx](frontend/src/pages/AdminPage.jsx)** (MODIFIED)
   - `currentTaskId` 상태 추가
   - ProgressBar 컴포넌트 통합
   - 완료 후 데이터 현황 새로고침

## 🚀 사용 방법

### 1. 백엔드 재시작

```bash
# 기존 백엔드 종료
pkill -f "uvicorn app.main:app"

# 새로 시작
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 프론트엔드 재시작

```bash
cd /Users/changrim/KingoPortfolio/frontend
npm run dev
```

### 3. 테스트

1. http://localhost:5173/admin 접속
2. "📈 주식 데이터만 수집" 버튼 클릭
3. **진행 상황 확인**:
   ```
   🔄 데이터 수집 진행 상황

   주식 데이터 수집 - 삼성전자 (005930)

   [████████████░░░░░░░░] 60%

   5 / 13 (38%)
   ✅ 성공: 5  ❌ 실패: 0  ⏳ 진행 중...
   ```

## 📊 ProgressTracker API

### 진행 상황 데이터 구조

```json
{
  "task_id": "stocks_a1b2c3d4",
  "description": "주식 데이터 수집",
  "total": 13,
  "current": 5,
  "status": "running",  // running | completed | failed
  "started_at": "2024-12-20T10:00:00",
  "updated_at": "2024-12-20T10:00:30",
  "completed_at": null,
  "success_count": 5,
  "failed_count": 0,
  "current_item": "삼성전자 (005930)",
  "error_message": null
}
```

### API 엔드포인트

#### 1. 특정 작업 조회
```bash
GET /admin/progress/{task_id}
Authorization: Bearer {token}

# 응답
{
  "task_id": "stocks_xxx",
  "current": 5,
  "total": 13,
  ...
}
```

#### 2. 모든 작업 조회
```bash
GET /admin/progress
Authorization: Bearer {token}

# 응답
{
  "stocks_xxx": { ... },
  "etfs_yyy": { ... }
}
```

#### 3. 진행 상황 삭제
```bash
DELETE /admin/progress/{task_id}
Authorization: Bearer {token}

# 응답
{
  "status": "success",
  "message": "Progress cleared"
}
```

## 💡 작동 원리

### 백엔드: 진행 상황 추적

```python
# 1. 작업 시작
progress_tracker.start_task(task_id, total_count, "주식 데이터 수집")

# 2. 진행 중 업데이트
for idx, (ticker, name) in enumerate(stocks_list, 1):
    progress_tracker.update_progress(
        task_id,
        current=idx,
        current_item=f"{name} ({ticker})",
        success=True
    )

# 3. 완료
progress_tracker.complete_task(task_id, "completed")
```

### 프론트엔드: 폴링 시스템

```javascript
// 1. task_id 받기
const response = await api.loadStocks();
setCurrentTaskId(response.data.task_id);

// 2. ProgressBar 컴포넌트가 자동으로 폴링 시작
<ProgressBar taskId={currentTaskId} onComplete={handleProgressComplete} />

// 3. 1초마다 진행 상황 조회
const interval = setInterval(async () => {
  const progress = await api.getProgress(taskId);
  setProgress(progress.data);

  if (progress.data.status === 'completed') {
    clearInterval(interval);
    onComplete(progress.data);
  }
}, 1000);
```

## 🔧 향후 개선 사항

### 1. WebSocket 사용 (선택)
현재는 HTTP 폴링을 사용하지만, 더 효율적인 WebSocket으로 변경 가능:

```python
# backend/app/websocket.py
from fastapi import WebSocket

@router.websocket("/ws/progress/{task_id}")
async def progress_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    while True:
        progress = progress_tracker.get_progress(task_id)
        await websocket.send_json(progress)
        if progress["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(1)
```

### 2. 백그라운드 태스크
FastAPI BackgroundTasks를 사용하여 비동기 처리:

```python
from fastapi import BackgroundTasks

@router.post("/load-stocks")
async def load_stocks(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    task_id = f"stocks_{uuid.uuid4().hex[:8]}"

    # 백그라운드에서 실행
    background_tasks.add_task(
        DataLoaderService.load_korean_stocks,
        db,
        task_id
    )

    return {
        "status": "started",
        "task_id": task_id
    }
```

### 3. 진행 상황 영구 저장
Redis나 DB에 진행 상황 저장:

```python
# Redis 사용 예시
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def start_task(task_id, total, description):
    progress = {
        "task_id": task_id,
        "total": total,
        ...
    }
    redis_client.setex(
        f"progress:{task_id}",
        3600,  # 1시간 TTL
        json.dumps(progress)
    )
```

## 📋 테스트 시나리오

### 1. 정상 수집
1. 주식 데이터 수집 버튼 클릭
2. 진행률 0% → 100% 확인
3. 성공 개수 증가 확인
4. 완료 메시지 표시 확인

### 2. 부분 실패
1. 일부 종목 수집 실패 시
2. 실패 개수 증가 확인
3. 에러 메시지 표시 확인
4. 전체 작업은 계속 진행

### 3. 여러 작업 동시 실행
1. 주식 수집 시작
2. 다른 탭에서 ETF 수집 시작
3. 각각 독립적으로 진행 상황 추적

## 🐛 트러블슈팅

### 문제 1: 진행 상황이 업데이트되지 않음

**원인**: 백엔드가 재시작되어 메모리에서 진행 상황 손실

**해결**:
- 브라우저 새로고침
- 새로 데이터 수집 시작

### 문제 2: "Task not found" 에러

**원인**: task_id가 만료되거나 삭제됨

**해결**:
```bash
# 모든 진행 상황 확인
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/admin/progress

# 새로 수집 시작
```

### 문제 3: 폴링이 너무 느림

**해결**: ProgressBar.jsx에서 폴링 간격 조정

```javascript
}, 500); // 1000ms → 500ms로 변경
```

## 📚 관련 문서

- [DATA_COLLECTION_GUIDE.md](DATA_COLLECTION_GUIDE.md) - 데이터 수집 전체 가이드
- [ADMIN_TROUBLESHOOTING.md](ADMIN_TROUBLESHOOTING.md) - 관리자 페이지 문제 해결
- [QUICK_START.md](QUICK_START.md) - 빠른 시작 가이드

---

**작성일**: 2024-12-20
**버전**: 1.0
**상태**: ✅ 구현 완료
**기능**: 실시간 진행 상황 모니터링
