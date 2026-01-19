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

  const health = http.get(`${BASE_URL}/api/v1/health`, { headers });
  check(health, { "health 200": (r) => r.status === 200 });

  const portfolio = http.get(
    `${BASE_URL}/api/v1/portfolios/public/sample`,
    { headers }
  );
  check(portfolio, { "portfolio 200": (r) => r.status === 200 });

  const metrics = http.get(`${BASE_URL}/api/v1/metrics/sample`, { headers });
  check(metrics, { "metrics 200": (r) => r.status === 200 });

  const guard = http.get(`${BASE_URL}/api/v1/recommendations`, { headers });
  check(guard, {
    "guard blocked": (r) => r.status === 404 || r.status === 403,
  });

  sleep(1);
}
