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

  const guard = http.get(`${BASE_URL}/api/v1/recommendations`, {
    headers,
    tags: { type: "guard" },
  });
  check(guard, { "guard blocked": (r) => r.status === 404 || r.status === 403 });

  sleep(1);
}
