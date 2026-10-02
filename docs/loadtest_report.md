# Load test report (Serving)

- Date: 2026-10-02 20:24
- Tool: Locust, 50 concurrent users, duration 2m
- Traffic mix: /predict 10 : /predict_batch (20 rows) 1 : /health 1
- Raw results: `loadtest/results/run_stats.csv`

## SLO check (targets from `configs/slo.yaml`)

| SLO | Measured | Target | Result |
|---|---:|---:|:---:|
| p50 latency /predict | 1100 ms | <= 50 ms | FAIL |
| p95 latency /predict | 1500 ms | <= 200 ms | FAIL |
| error rate (all requests) | 0.00% | <= 1.00% | PASS |
| availability | 100.00% | >= 99.00% | PASS |

## Per-endpoint latency

| Endpoint | Requests | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Error rate |
|---|---:|---:|---:|---:|---:|---:|
| GET /health | 316 | 2.7 | 190 | 390 | 510 | 0.00% |
| POST /predict | 3537 | 29.8 | 1100 | 1500 | 1800 | 0.00% |
| POST /predict_batch | 394 | 3.3 | 1100 | 1500 | 1800 | 0.00% |
| Aggregated | 4247 | 35.7 | 1100 | 1400 | 1800 | 0.00% |

**Overall: SLO missed - see FAIL rows**
