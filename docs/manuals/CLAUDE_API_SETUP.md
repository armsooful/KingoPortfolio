# Claude API 연동 가이드

## 개요

KingoPortfolio는 Anthropic의 Claude AI를 사용하여 투자성향 진단 결과에 대한 개인화된 분석과 조언을 제공합니다.

## 기능

Claude AI는 다음과 같은 분석을 제공합니다:

1. **개인화된 투자성향 분석**: 사용자의 설문 답변 패턴을 바탕으로 구체적인 투자 성향 설명
2. **투자 조언**: 투자성향에 적합한 구체적인 투자 전략 및 자산 배분 가이드
3. **위험 주의사항**: 투자 시 반드시 주의해야 할 리스크 및 위험 관리 방법

## 설정 방법

### 1. API 키 발급

1. [Anthropic Console](https://console.anthropic.com/)에 접속
2. 계정 생성 또는 로그인
3. API Keys 메뉴에서 새 API 키 생성
4. 발급받은 API 키를 안전하게 저장

### 2. 환경 변수 설정

#### 백엔드 설정

`backend/.env` 파일을 생성하고 다음 내용을 추가:

```bash
# Claude AI API Key
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

또는 시스템 환경변수로 설정:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

### 3. 패키지 설치

백엔드 의존성 설치:

```bash
cd backend
pip install -r requirements.txt
```

`requirements.txt`에 `anthropic==0.40.0`이 포함되어 있어야 합니다.

### 4. 서버 실행

```bash
cd backend
uvicorn app.main:app --reload
```

## 작동 방식

### API 호출 흐름

1. **사용자 설문 제출** → `POST /diagnosis/submit`
2. **투자성향 진단 계산** (기존 로직)
3. **Claude AI 분석 요청** (비동기, 선택적)
   - 설문 답변 데이터
   - 진단 결과 (투자성향, 점수, 신뢰도)
   - 월 투자 가능액 (옵션)
4. **AI 분석 결과 반환**
   - `personalized_analysis`: 개인화된 분석
   - `investment_advice`: 투자 조언
   - `risk_warning`: 위험 주의사항
5. **프론트엔드에 표시**

### 에러 핸들링

- API 키가 없거나 잘못된 경우: 기본 템플릿 응답 사용
- Claude API 호출 실패 시: 진단은 정상 진행, AI 분석만 생략
- 사용자는 AI 분석 없이도 기본 진단 결과를 받을 수 있음

## 코드 구조

### 백엔드

```
backend/
├── app/
│   ├── services/
│   │   └── claude_service.py       # Claude AI 서비스
│   ├── routes/
│   │   └── diagnosis.py            # AI 분석 통합
│   ├── config.py                   # API 키 설정
│   └── schemas.py                  # AI 응답 스키마
```

### 주요 파일

#### `app/services/claude_service.py`

```python
class ClaudeService:
    def analyze_investment_profile(
        self,
        answers: List[DiagnosisAnswerRequest],
        investment_type: str,
        score: float,
        confidence: float,
        monthly_investment: int = None
    ) -> Dict[str, str]:
        """투자성향 진단 결과를 Claude AI가 분석"""
        # Claude API 호출 및 응답 파싱
```

#### `app/routes/diagnosis.py`

```python
@router.post("/submit")
async def submit_survey(...):
    # 기존 진단 로직
    investment_type, score, confidence = calculate_diagnosis(...)

    # Claude AI 분석 추가 (선택적)
    try:
        claude_service = get_claude_service()
        ai_analysis = claude_service.analyze_investment_profile(...)
        response_data["ai_analysis"] = ai_analysis
    except Exception as e:
        # AI 분석 실패 시 무시
        response_data["ai_analysis"] = None
```

### 프론트엔드

```
frontend/
└── src/
    ├── pages/
    │   └── DiagnosisResultPage.jsx  # AI 분석 결과 표시
    └── styles/
        └── App.css                  # AI 섹션 스타일
```

## API 응답 예시

### 성공 응답

```json
{
  "diagnosis_id": "uuid-1234",
  "investment_type": "moderate",
  "score": 5.5,
  "confidence": 0.87,
  "description": "안정성과 수익성을 모두 추구하는...",
  "characteristics": [...],
  "recommended_ratio": {...},
  "expected_annual_return": "6-8%",
  "ai_analysis": {
    "personalized_analysis": "귀하의 설문 응답을 분석한 결과...",
    "investment_advice": "중도형 투자자로서 다음과 같은 전략을 추천합니다...",
    "risk_warning": "시장 변동성에 흔들리지 않는 투자 원칙이 필요합니다..."
  },
  "created_at": "2025-12-19T..."
}
```

### AI 분석 없는 응답

```json
{
  "diagnosis_id": "uuid-1234",
  "investment_type": "moderate",
  "score": 5.5,
  "confidence": 0.87,
  "description": "안정성과 수익성을 모두 추구하는...",
  "characteristics": [...],
  "recommended_ratio": {...},
  "expected_annual_return": "6-8%",
  "ai_analysis": null,
  "created_at": "2025-12-19T..."
}
```

## 비용 고려사항

### Claude API 가격

- 모델: `claude-3-5-sonnet-20241022`
- 입력: ~$3 per million tokens
- 출력: ~$15 per million tokens

### 예상 비용

각 진단당:
- 입력: ~500 토큰
- 출력: ~800 토큰
- **예상 비용: 약 $0.01-0.02 per 진단**

월 1,000명 사용 시 약 $10-20 예상

### 비용 최적화 방안

1. **캐싱**: 유사한 진단 결과는 캐시 활용
2. **토큰 제한**: `max_tokens=2000`으로 제한
3. **선택적 활성화**: 유료 사용자만 AI 분석 제공
4. **배치 처리**: 여러 요청을 모아서 처리

## 테스트

### 로컬 테스트

```bash
# API 키 설정
export ANTHROPIC_API_KEY="your-key"

# 백엔드 실행
cd backend
uvicorn app.main:app --reload

# 프론트엔드 실행
cd frontend
npm run dev
```

### API 직접 테스트

```bash
curl -X POST "http://localhost:8000/diagnosis/submit" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": 1, "answer_value": 3},
      {"question_id": 2, "answer_value": 4}
    ],
    "monthly_investment": 100
  }'
```

## 트러블슈팅

### API 키 오류

```
ValueError: ANTHROPIC_API_KEY가 설정되지 않았습니다.
```

**해결**: `.env` 파일에 `ANTHROPIC_API_KEY` 추가

### Claude API 호출 실패

```
Claude API 호출 실패: API connection error
```

**해결**:
- 인터넷 연결 확인
- API 키 유효성 확인
- Anthropic API 상태 확인 (https://status.anthropic.com)

### AI 분석이 표시되지 않음

**확인사항**:
1. API 키가 올바르게 설정되었는지
2. 백엔드 로그에서 에러 메시지 확인
3. 브라우저 개발자 도구에서 응답 데이터 확인

## 프로덕션 배포

### 환경변수 설정

**Render.com**:
1. Dashboard → Environment
2. `ANTHROPIC_API_KEY` 추가
3. Save Changes

**Vercel (프론트엔드는 필요 없음)**:
- 백엔드에서만 API 키 사용

### 보안 권장사항

1. **API 키 보호**: 절대 코드에 하드코딩하지 말 것
2. **환경변수 사용**: 모든 민감 정보는 환경변수로 관리
3. **로그 주의**: API 키가 로그에 노출되지 않도록 주의
4. **요청 제한**: Rate limiting 구현 (DDoS 방지)

## 참고 자료

- [Anthropic API 문서](https://docs.anthropic.com/)
- [Claude Models](https://docs.anthropic.com/en/docs/about-claude/models)
- [API 가격 정보](https://www.anthropic.com/pricing)
- [Python SDK](https://github.com/anthropics/anthropic-sdk-python)

## 라이선스

이 프로젝트는 Claude API를 사용하며, Anthropic의 이용 약관을 준수합니다.

---

**문의**: 문제가 발생하면 GitHub Issues에 보고해주세요.
