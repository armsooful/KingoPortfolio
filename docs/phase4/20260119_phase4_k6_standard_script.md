# Phase 4 k6 성능 테스트 표준 스크립트 초안

## 목적
- 재현 가능한 성능/SLA 측정
- Phase 3 검증 보고서에 Append 가능한 결과 확보

## 가정
- 대상 API는 인증이 필요 없거나 테스트 토큰이 준비되어 있다.
- 기본 엔드포인트는 환경 변수로 주입한다.

## 실행 방법
```bash
k6 run \
  -e BASE_URL=https://api.example.com \
  -e AUTH_TOKEN=changeme \
  -e VUS=50 \
  -e DURATION=10m \
  scripts/k6/phase4_standard.js
```

## 스크립트 (초안)
아래 파일로 저장: `scripts/k6/phase4_standard.js`

```javascript
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

const VUS = Number(__ENV.VUS || 30);
const DURATION = __ENV.DURATION || "10m";

export const options = {
  scenarios: {
    warmup: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [{ duration: "2m", target: Math.ceil(VUS * 0.5) }],
      gracefulStop: "30s",
    },
    steady: {
      executor: "constant-vus",
      vus: VUS,
      duration: DURATION,
      startTime: "2m",
      gracefulStop: "30s",
    },
    spike: {
      executor: "ramping-vus",
      startVUs: VUS,
      stages: [
        { duration: "30s", target: Math.ceil(VUS * 2) },
        { duration: "90s", target: Math.ceil(VUS * 2) },
        { duration: "30s", target: VUS },
      ],
      startTime: "12m",
      gracefulStop: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.001"],
    http_req_duration: ["p(95)<500", "p(99)<1500"],
  },
};

function authHeaders() {
  return AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {};
}

export default function () {
  const headers = authHeaders();

  // Health check
  const health = http.get(`${BASE_URL}/api/v1/health`, { headers });
  check(health, { "health 200": (r) => r.status === 200 });

  // U-1 public portfolio read
  const portfolio = http.get(
    `${BASE_URL}/api/v1/portfolios/public/sample`,
    { headers }
  );
  check(portfolio, { "portfolio 200": (r) => r.status === 200 });

  // U-2 metrics
  const metrics = http.get(`${BASE_URL}/api/v1/metrics/sample`, { headers });
  check(metrics, { "metrics 200": (r) => r.status === 200 });

  // Guard: recommendations should be blocked (expect 404 or 403)
  const guard = http.get(`${BASE_URL}/api/v1/recommendations`, { headers });
  check(guard, {
    "guard blocked": (r) => r.status === 404 || r.status === 403,
  });

  sleep(1);
}
```

## 측정 항목
- API 응답 p95 < 500ms
- API 응답 p99 < 1500ms
- 5xx 오류율 < 0.1%
- Guard 응답 p95 < 200ms (별도 분석 권장)

## 결과 기록
- 결과는 `docs/reports/foresto_compass_u3_verification_report_YYYYMMDD.md`에 Append
- 스크립트 실행 로그 및 환경 정보 포함
