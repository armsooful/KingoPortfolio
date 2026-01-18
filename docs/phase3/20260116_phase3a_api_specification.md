# Phase 3-A API 명세서
최초작성일자: 2026-01-16
최종수정일자: 2026-01-18

---
생성일자: 2026-01-16
최종수정일자: 2026-01-17
---

# Phase 3-A API 명세서
## 포트폴리오 설명·해석 API

## 1. 개요
Phase 3-A API는 포트폴리오 성과 지표를 입력받아 설명형 해석 데이터를 반환한다.

## 2. API 목록

### 2.1 포트폴리오 성과 해석
- URL: /api/v1/analysis/explain
- Method: POST

#### Request
```json
{
  "portfolio_id": "string",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD"
}
```

#### Response
```json
{
  "summary": "string",
  "performance_explanation": [
    {
      "metric": "CAGR",
      "description": "string"
    }
  ],
  "risk_explanation": "string"
}
```

## 3. 유의사항
- 모든 설명은 투자 판단을 제공하지 않음
- 추천, 최적 표현 사용 금지

## 4. 에러 코드
- 400: Invalid Request
- 404: Portfolio Not Found
- 500: Internal Server Error
