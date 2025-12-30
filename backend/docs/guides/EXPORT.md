# 데이터 내보내기 기능

## 개요

KingoPortfolio에 데이터 내보내기 기능이 구현되었습니다. 사용자는 투자 성향 진단 결과를 CSV 또는 Excel 형식으로 다운로드할 수 있습니다.

## 주요 파일

- [`app/utils/export.py`](app/utils/export.py) - 데이터 내보내기 유틸리티 함수
- [`app/routes/diagnosis.py`](app/routes/diagnosis.py) - 진단 결과 내보내기 엔드포인트 (lines 272-453)
- [`tests/unit/test_export.py`](tests/unit/test_export.py) - 내보내기 기능 테스트

## 기능

### 1. 진단 결과 CSV 다운로드 (GET /diagnosis/{diagnosis_id}/export/csv)

특정 진단 결과를 CSV 파일로 다운로드합니다.

#### 요청

```bash
GET /diagnosis/{diagnosis_id}/export/csv
Authorization: Bearer {access_token}
```

#### 경로 매개변수

- `diagnosis_id` (필수): 진단 ID

#### 응답 (200 OK)

CSV 파일 다운로드 (Content-Type: text/csv; charset=utf-8)

**파일명 형식**: `diagnosis_{short_id}_{timestamp}.csv`

**CSV 구조**:
```
=== 진단 기본 정보 ===
항목,값
진단 ID,dia_abc123xyz
투자 성향,moderate
점수,7.5
신뢰도,85.0%
월 투자액,100만원
진단일시,2025-12-29 10:00:00

=== 투자 성향 특징 ===
1. 안정적인 수익을 선호합니다
2. 중장기 투자 관점을 가지고 있습니다
...

=== 추천 자산 배분 ===
자산,비율
주식,50%
채권,30%
현금,20%

기대 연 수익률: 5-7%
```

#### 에러 응답

**401 Unauthorized** - 인증 실패

```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden** - 권한 없음 (다른 사용자의 진단)

```json
{
  "detail": "You don't have permission to export this diagnosis"
}
```

**404 Not Found** - 진단 결과 없음

```json
{
  "detail": "Diagnosis {diagnosis_id} not found"
}
```

### 2. 진단 결과 Excel 다운로드 (GET /diagnosis/{diagnosis_id}/export/excel)

특정 진단 결과를 Excel 파일로 다운로드합니다 (여러 시트 포함).

#### 요청

```bash
GET /diagnosis/{diagnosis_id}/export/excel
Authorization: Bearer {access_token}
```

#### 경로 매개변수

- `diagnosis_id` (필수): 진단 ID

#### 응답 (200 OK)

Excel 파일 다운로드 (Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)

**파일명 형식**: `diagnosis_{short_id}_{timestamp}.xlsx`

**Excel 구조** (3개 시트):

1. **기본 정보** 시트
   - 제목: "투자 성향 진단 결과"
   - 진단 ID, 투자 성향, 점수, 신뢰도, 월 투자액, 진단일시, 설명

2. **투자 성향 특징** 시트
   - 투자 성향별 상세 특징 목록

3. **추천 자산 배분** 시트
   - 자산별 추천 비율
   - 기대 연 수익률

**스타일링**:
- 헤더: 파란색 배경, 흰색 텍스트, 굵게
- 테두리: 모든 셀에 얇은 테두리
- 컬럼 너비: 자동 조정

### 3. 진단 이력 CSV 다운로드 (GET /diagnosis/history/export/csv)

현재 사용자의 모든 진단 이력을 CSV 파일로 다운로드합니다.

#### 요청

```bash
GET /diagnosis/history/export/csv?limit=100
Authorization: Bearer {access_token}
```

#### 쿼리 매개변수

- `limit` (선택): 조회할 최대 개수 (기본값: 100)

#### 응답 (200 OK)

CSV 파일 다운로드

**파일명 형식**: `diagnosis_history_{timestamp}.csv`

**CSV 구조**:
```
진단 ID,투자 성향,점수,신뢰도,월 투자액,진단일시
dia_abc123,conservative,5.5,80.0%,50만원,2025-12-20 09:00:00
dia_def456,moderate,7.5,85.0%,100만원,2025-12-25 14:30:00
dia_ghi789,aggressive,9.0,90.0%,200만원,2025-12-29 10:00:00
```

#### 에러 응답

**404 Not Found** - 진단 이력 없음

```json
{
  "detail": "No diagnosis history found"
}
```

## 사용 예시

### Python (requests)

```python
import requests

# 로그인
login_response = requests.post("http://localhost:8000/auth/login", json={
    "email": "user@example.com",
    "password": "password123"
})
token = login_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# 1. 최신 진단 결과 조회
latest = requests.get("http://localhost:8000/diagnosis/me", headers=headers)
diagnosis_id = latest.json()["diagnosis_id"]

# 2. CSV 다운로드
csv_response = requests.get(
    f"http://localhost:8000/diagnosis/{diagnosis_id}/export/csv",
    headers=headers
)

# 파일로 저장
with open("my_diagnosis.csv", "wb") as f:
    f.write(csv_response.content)

# 3. Excel 다운로드
excel_response = requests.get(
    f"http://localhost:8000/diagnosis/{diagnosis_id}/export/excel",
    headers=headers
)

with open("my_diagnosis.xlsx", "wb") as f:
    f.write(excel_response.content)

# 4. 진단 이력 CSV 다운로드
history_response = requests.get(
    "http://localhost:8000/diagnosis/history/export/csv?limit=50",
    headers=headers
)

with open("diagnosis_history.csv", "wb") as f:
    f.write(history_response.content)

print("모든 파일이 다운로드되었습니다!")
```

### JavaScript (fetch)

```javascript
// 로그인
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});
const { access_token } = await loginResponse.json();

const headers = {
  'Authorization': `Bearer ${access_token}`
};

// 1. 최신 진단 결과 조회
const latest = await fetch('http://localhost:8000/diagnosis/me', { headers });
const { diagnosis_id } = await latest.json();

// 2. CSV 다운로드
const csvResponse = await fetch(
  `http://localhost:8000/diagnosis/${diagnosis_id}/export/csv`,
  { headers }
);

const csvBlob = await csvResponse.blob();
const csvUrl = window.URL.createObjectURL(csvBlob);
const csvLink = document.createElement('a');
csvLink.href = csvUrl;
csvLink.download = 'my_diagnosis.csv';
csvLink.click();

// 3. Excel 다운로드
const excelResponse = await fetch(
  `http://localhost:8000/diagnosis/${diagnosis_id}/export/excel`,
  { headers }
);

const excelBlob = await excelResponse.blob();
const excelUrl = window.URL.createObjectURL(excelBlob);
const excelLink = document.createElement('a');
excelLink.href = excelUrl;
excelLink.download = 'my_diagnosis.xlsx';
excelLink.click();

console.log('파일 다운로드 완료!');
```

### cURL

```bash
# 1. 로그인
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}' \
  | jq -r '.access_token')

# 2. 최신 진단 결과 조회
DIAGNOSIS_ID=$(curl -X GET http://localhost:8000/diagnosis/me \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.diagnosis_id')

# 3. CSV 다운로드
curl -X GET http://localhost:8000/diagnosis/$DIAGNOSIS_ID/export/csv \
  -H "Authorization: Bearer $TOKEN" \
  -o my_diagnosis.csv

# 4. Excel 다운로드
curl -X GET http://localhost:8000/diagnosis/$DIAGNOSIS_ID/export/excel \
  -H "Authorization: Bearer $TOKEN" \
  -o my_diagnosis.xlsx

# 5. 진단 이력 CSV 다운로드
curl -X GET "http://localhost:8000/diagnosis/history/export/csv?limit=50" \
  -H "Authorization: Bearer $TOKEN" \
  -o diagnosis_history.csv

echo "모든 파일이 다운로드되었습니다!"
```

## 유틸리티 함수

### generate_csv()

딕셔너리 리스트를 CSV 문자열로 변환합니다.

```python
from app.utils.export import generate_csv

data = [
    {"이름": "홍길동", "나이": 30, "직업": "개발자"},
    {"이름": "김철수", "나이": 25, "직업": "디자이너"}
]

csv_content = generate_csv(data)
# 결과: CSV 형식의 문자열
```

### generate_excel()

딕셔너리 리스트를 Excel 바이트로 변환합니다 (스타일 포함).

```python
from app.utils.export import generate_excel

data = [
    {"이름": "홍길동", "나이": 30, "직업": "개발자"},
    {"이름": "김철수", "나이": 25, "직업": "디자이너"}
]

excel_bytes = generate_excel(data, title="직원 목록")

# 파일로 저장
with open("employees.xlsx", "wb") as f:
    f.write(excel_bytes)
```

### generate_diagnosis_csv()

진단 결과를 CSV 형식으로 변환합니다 (섹션 구분 포함).

```python
from app.utils.export import generate_diagnosis_csv

diagnosis_data = {
    "diagnosis_id": "dia_123",
    "investment_type": "moderate",
    "score": 7.5,
    "confidence": 0.85,
    "monthly_investment": 100,
    "created_at": "2025-12-29T10:00:00Z",
    "description": "안정적인 투자 성향",
    "characteristics": ["위험 회피 성향", "장기 투자 선호"],
    "recommended_ratio": {"주식": 50, "채권": 30, "현금": 20},
    "expected_annual_return": "5-7%"
}

csv_content = generate_diagnosis_csv(diagnosis_data)
```

### generate_diagnosis_excel()

진단 결과를 Excel 파일로 변환합니다 (여러 시트).

```python
from app.utils.export import generate_diagnosis_excel

diagnosis_data = { ... }  # 위와 동일

excel_bytes = generate_diagnosis_excel(diagnosis_data)

# 파일로 저장
with open("diagnosis.xlsx", "wb") as f:
    f.write(excel_bytes)
```

## 테스트

### 테스트 구조

`tests/unit/test_export.py`에 12개의 테스트가 있습니다:

```
TestExportEndpoints (8개)
├── test_export_diagnosis_csv_success
├── test_export_diagnosis_excel_success
├── test_export_diagnosis_csv_unauthorized
├── test_export_diagnosis_csv_not_found
├── test_export_diagnosis_csv_forbidden
├── test_export_diagnosis_excel_forbidden
├── test_export_history_csv_success (SKIPPED)
└── test_export_history_csv_no_history

TestExportUtils (4개)
├── test_generate_csv
├── test_generate_excel
├── test_generate_diagnosis_csv
└── test_generate_diagnosis_excel
```

### 테스트 실행

```bash
# 내보내기 테스트만 실행
pytest tests/unit/test_export.py -v

# 전체 테스트 스위트 실행
pytest tests/ -v
```

### 테스트 결과

- **총 테스트**: 135개
- **통과**: 134개
- **스킵**: 1개 (DB 격리 이슈)
- **내보내기 테스트**: 11개 통과

## 보안 고려사항

### 1. 인증 및 권한

- 모든 내보내기 엔드포인트는 JWT 토큰 인증 필수
- 사용자는 자신의 진단 결과만 다운로드 가능
- 다른 사용자의 진단 결과 접근 시 403 Forbidden

### 2. 데이터 보호

- 민감한 정보는 포함하지 않음
- 파일 다운로드 시 즉시 생성 (서버에 저장하지 않음)
- 파일명에 타임스탬프 포함하여 캐시 방지

### 3. 리소스 관리

- 대용량 데이터 방지를 위한 limit 매개변수 (기본값: 100)
- 메모리 효율적인 스트리밍 방식 사용
- 파일 생성 후 즉시 반환 (임시 파일 없음)

### 4. 입력 검증

- diagnosis_id 존재 여부 확인
- 사용자 권한 검증
- limit 매개변수 범위 제한 가능 (향후 개선)

## 성능 최적화

### 1. 메모리 효율

- `io.StringIO` 및 `io.BytesIO` 사용으로 메모리 내 처리
- 임시 파일 생성하지 않음
- 대용량 데이터의 경우 스트리밍 가능

### 2. 응답 속도

- 데이터 조회 후 즉시 변환
- 캐싱 불필요 (사용자별 데이터)
- 비동기 처리로 빠른 응답

### 3. 데이터베이스

- 필요한 컬럼만 조회
- 인덱스 활용 (user_id, created_at)
- limit으로 결과 제한

## 의존성

### 필수 라이브러리

```
pandas>=2.3.3
openpyxl>=3.1.5
fastapi>=0.104.1
```

### 설치

```bash
pip install pandas openpyxl
```

## 에러 처리

모든 에러는 일관된 형식으로 반환됩니다:

```json
{
  "detail": "에러 메시지"
}
```

또는

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 친화적인 메시지",
    "status": 404
  }
}
```

### 주요 에러 코드

| 코드 | 상태 | 설명 |
|------|------|------|
| - | 401 | 인증 실패 (토큰 없음 또는 유효하지 않음) |
| - | 403 | 권한 없음 (다른 사용자의 데이터) |
| - | 404 | 리소스 없음 (진단 결과 또는 이력 없음) |

## API 문서

Swagger UI에서 인터랙티브한 API 문서를 확인할 수 있습니다:

```bash
# 서버 시작
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload

# 브라우저에서 접속
# http://localhost:8000/docs
```

### 문서 탐색

1. Swagger UI 우측 상단 "Authorize" 버튼 클릭
2. `/auth/login`으로 토큰 획득
3. `Bearer {access_token}` 입력
4. "Authorize" 클릭
5. **Diagnosis** 태그 아래에서 내보내기 엔드포인트 확인:
   - GET /diagnosis/{diagnosis_id}/export/csv
   - GET /diagnosis/{diagnosis_id}/export/excel
   - GET /diagnosis/history/export/csv

## 통계

### 코드 변경

- **추가된 파일**: 3개
  - app/utils/export.py (147 lines)
  - app/utils/__init__.py (11 lines)
  - tests/unit/test_export.py (434 lines)

- **수정된 파일**: 1개
  - app/routes/diagnosis.py: +186 lines (3개 엔드포인트)

### 테스트

- **새 테스트**: 12개
- **테스트 통과**: 11개 (1개 스킵)
- **전체 테스트**: 123개 → 135개 (+12개)

### 기능

- **새 엔드포인트**: 3개
- **유틸리티 함수**: 4개
- **지원 형식**: CSV, Excel

## 향후 개선 사항

- [ ] PDF 형식 지원
- [ ] 차트 및 그래프 포함 (Excel)
- [ ] 다중 진단 결과 비교 내보내기
- [ ] 이메일로 파일 전송 기능
- [ ] 스케줄링 된 내보내기 (예: 월간 리포트)
- [ ] 커스텀 템플릿 지원
- [ ] 압축 파일 (ZIP) 지원 (여러 파일)
- [ ] 데이터 필터링 옵션
- [ ] 통계 요약 포함
- [ ] 국제화 (다국어 지원)

## 관련 문서

- [프로필 관리 가이드](PROFILE.md)
- [비밀번호 재설정 가이드](PASSWORD_RESET.md)
- [API 문서화 가이드](API_DOCUMENTATION.md)
- [에러 핸들링 시스템](ERROR_HANDLING.md)

## 문의

데이터 내보내기 기능 관련 문의사항은 백엔드 팀에 문의해주세요.

---

**마지막 업데이트**: 2025-12-29
**버전**: 1.0.0
**테스트 통과**: 134/135 (99.3%)
**작성자**: Claude Code (AI Assistant)
