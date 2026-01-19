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
import { Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

const VUS = Number(__ENV.VUS || 30);
const DURATION = __ENV.DURATION || "10m";

const http5xxRate = new Rate("http_5xx_rate");

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
    http_req_duration: ["p(95)<500", "p(99)<1500"],
    http_5xx_rate: ["rate<0.001"],
  },
};

function authHeaders() {
  return AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {};
}

export default function () {
  const headers = authHeaders();

  const health = http.get(`${BASE_URL}/health`, { headers });
  check(health, { "health 200": (r) => r.status === 200 });
  http5xxRate.add(health.status >= 500);

  const docs = http.get(`${BASE_URL}/docs`, { headers });
  check(docs, { "docs 200": (r) => r.status === 200 });
  http5xxRate.add(docs.status >= 500);

  const openapi = http.get(`${BASE_URL}/openapi.json`, { headers });
  check(openapi, { "openapi 200": (r) => r.status === 200 });
  http5xxRate.add(openapi.status >= 500);

  const robots = http.get(`${BASE_URL}/robots.txt`, { headers });
  check(robots, { "robots 200": (r) => r.status === 200 });
  http5xxRate.add(robots.status >= 500);

  // Guard: recommendations should be blocked (expect 404 or 403)
  const guard = http.get(`${BASE_URL}/api/v1/recommendations`, {
    headers,
    tags: { type: "guard" },
  });
  check(guard, { "guard blocked": (r) => r.status === 404 || r.status === 403 });

  sleep(1);
}
```

## 측정 항목
- API 응답 p95 < 500ms
- API 응답 p99 < 1500ms
- 5xx 오류율 < 0.1% (`http_5xx_rate` 기준)
- Guard 응답 p95 < 200ms (별도 분석 권장)

참고: Guard 경로는 404/403 응답이 의도된 동작이므로 `http_req_failed` 값이 증가할 수 있다.

## 결과 기록
- 결과는 `docs/reports/foresto_compass_u3_verification_report_YYYYMMDD.md`에 Append
- 스크립트 실행 로그 및 환경 정보 포함
