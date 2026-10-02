# Load test report (Serving)

- Date: 2026-10-02 21:35
- Configuration: 2 workers + batching 32
- Tool: Locust, 50 concurrent users, duration 2m
- Traffic mix: /predict 10 : /predict_batch (20 rows) 1 : /health 1
- Raw results: `loadtest/results/w2b32_stats.csv`

## SLO check: 2 workers + batching 32 (targets from `configs/slo.yaml`)

| SLO | Measured | Target | Result |
|---|---:|---:|:---:|
| p50 latency /predict | 74 ms | <= 50 ms | FAIL |
| p95 latency /predict | 99 ms | <= 200 ms | PASS |
| error rate (all requests) | 0.00% | <= 1.00% | PASS |
| availability | 100.00% | >= 99.00% | PASS |

**Overall: SLO missed - see FAIL rows**

## Before / after optimization

| Configuration | /predict p50 | /predict p95 | /predict p99 | Total req/s | Errors | p50 <= 50 | p95 <= 200 |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| 1 worker (baseline) | 1100 ms | 1500 ms | 1800 ms | 35.7 | 0.00% | FAIL | FAIL |
| 2 workers | 160 ms | 300 ms | 420 ms | 107.0 | 0.02% | FAIL | FAIL |
| 4 workers | 75 ms | 170 ms | 280 ms | 130.0 | 0.00% | FAIL | PASS |
| 1 worker + batching 32 | 68 ms | 110 ms | 170 ms | 133.6 | 0.00% | FAIL | PASS |
| 2 workers + batching 32 | 74 ms | 99 ms | 120 ms | 133.1 | 0.00% | FAIL | PASS |

## Per-endpoint latency: 2 workers + batching 32

| Endpoint | Requests | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Error rate |
|---|---:|---:|---:|---:|---:|---:|
| GET /health | 1295 | 10.8 | 9 | 19 | 29 | 0.00% |
| POST /predict | 13310 | 111.3 | 74 | 99 | 120 | 0.00% |
| POST /predict_batch | 1321 | 11.0 | 74 | 100 | 130 | 0.00% |
| Aggregated | 15926 | 133.1 | 72 | 98 | 120 | 0.00% |

<!-- notes: everything below is kept when this report is regenerated -->

## Analysis

(write the findings here)
