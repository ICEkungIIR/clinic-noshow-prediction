# Serving & Infra (Issue #3)

ผู้รับผิดชอบ: ภูรินทร์ ศรีฐาน

## ภาพรวม

API โหลดโมเดล **champion** จาก MLflow Registry (`models:/clinic-noshow@champion`) ซึ่งเป็น
sklearn Pipeline ทั้งก้อน (feature builder → preprocessing → LightGBM Exp 2) จาก workstream Model/Registry
ดังนั้น preprocessing ตอน serve คือโค้ดชุดเดียวกับตอน train (`src/noshow/features/`) ไม่มี training-serving skew

threshold อ่านจาก tag `threshold` ของ model version เดียวกัน (ตั้งโดย `registry/manage.py`)
ถ้าไม่มี tag จะใช้ `model.selected_threshold` ใน `configs/params.yaml` และ override ได้ด้วย env `MODEL_THRESHOLD`

| ไฟล์ | หน้าที่ |
|---|---|
| `src/noshow/serving/app.py` | FastAPI endpoints + Prometheus metrics |
| `src/noshow/serving/schemas.py` | Pydantic schema ของ input/output และกฎ validation |
| `src/noshow/serving/model.py` | โหลดโมเดล/threshold จาก registry, ทำนาย, reload |
| `tests/test_serving_model.py`, `tests/test_serving_api.py` | unit + API tests (ใช้โมเดลจำลอง ไม่ต้องมี MLflow) |
| `loadtest/locustfile.py` | Locust load test |
| `scripts/check_slo.py` | เทียบผล load test กับ `configs/slo.yaml` → `docs/loadtest_report.md` |

## Endpoints

| Method | Path | ใช้ทำอะไร |
|---|---|---|
| GET | `/health` | liveness + version/threshold ของโมเดลที่โหลดอยู่ |
| POST | `/predict` | ทำนาย 1 นัดหมาย |
| POST | `/predict_batch` | ทำนาย 1–1000 นัดหมาย |
| POST | `/reload` | โหลด champion ใหม่หลัง promote/rollback โดยไม่ต้อง restart |
| GET | `/metrics` | Prometheus metrics |

ตัวอย่าง:

```bash
curl -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{
  "PatientId": 29872499824296, "Gender": "F",
  "ScheduledDay": "2016-05-04T08:00:00Z", "AppointmentDay": "2016-05-10",
  "Age": 45, "Neighbourhood": "JARDIM DA PENHA",
  "Scholarship": 0, "Hipertension": 1, "Diabetes": 0, "Alcoholism": 0,
  "Handcap": 0, "SMS_received": 1}'
# {"PatientId": 29872499824296.0, "noshow_score": 0.61, "alert": true, "threshold": 0.5, "model_version": "3"}
```

`noshow_score` มาจากโมเดลที่ใช้ class weight จึง**ไม่ใช่ความน่าจะเป็นที่ calibrate แล้ว**
ใช้จัดลำดับ/ตัดสินใจส่งเตือน (`alert`) ไม่ควรแสดงเป็น "โอกาสไม่มา xx%"

### กฎ validation (ตอบ 422 เมื่อผิด)

- ใช้ชื่อคอลัมน์เดียวกับข้อมูลดิบ ห้ามส่ง `No-show` และห้ามมี field เกิน
- `Gender` ∈ {F, M}, `Age` 0–120, flag ต่างๆ เป็น 0/1, `Handcap` 0–4
- `ScheduledDay` ต้องไม่หลัง `AppointmentDay` (กฎเดียวกับ `data/clean.py`)
- เวลาที่ไม่มี timezone ถือเป็น UTC เหมือนข้อมูล train; `Handcap` 2–4 ถูกยุบเป็น 1 เหมือนตอน clean
- `Neighbourhood` ถูกแปลงเป็นตัวพิมพ์ใหญ่; ค่าที่ไม่เคยเห็นยังทำนายได้ (`handle_unknown="ignore"`)

### พฤติกรรมเมื่อยังไม่มีโมเดล

API เปิดได้แม้ MLflow ยังไม่มี champion: thread เบื้องหลังจะลองโหลดใหม่ทุก 15 วินาที
ระหว่างนั้น `/predict` ตอบ **503** และ `/health` แสดง `model_loaded: false` พร้อม `last_error`
ถ้า `/reload` ล้มเหลว API จะใช้โมเดลเดิมต่อ (ไม่ล่ม)

## การตั้งค่า (env)

| ตัวแปร | ค่าเริ่มต้น | หมายเหตุ |
|---|---|---|
| `MLFLOW_TRACKING_URI` | – | ใน compose = `http://mlflow:5000` |
| `MODEL_URI` | `models:/clinic-noshow@champion` | ระบุ version ตรงได้ เช่น `models:/clinic-noshow/2` |
| `MODEL_PATH` | – | path โฟลเดอร์ MLflow model ในเครื่อง (dev แบบไม่มี server) |
| `MODEL_THRESHOLD` | tag ของ version | override threshold |
| `MODEL_LOAD_ON_STARTUP` | `1` | ตั้ง `0` เพื่อไม่โหลดตอนเริ่ม |

## วิธีรัน

```bash
make up                       # API + MLflow + Prefect + Prometheus + Grafana
make pipeline                 # train -> register -> gate -> promote champion
curl -X POST localhost:8000/reload   # หรือรอ background loader
curl localhost:8000/health
```

รันแบบไม่ใช้ Docker: `MLFLOW_TRACKING_URI=http://localhost:5001 make api`

Demo rollback: รัน rollback ของ registry แล้ว `POST /reload` → `/health` จะแสดง version ก่อนหน้า

## Load test และ SLO

```bash
make loadtest                          # 50 users, ramp 10/s, 2 นาที
make loadtest LT_USERS=100 LT_TIME=5m  # ปรับได้
```

ผลดิบอยู่ที่ `loadtest/results/run_stats.csv` และสรุป PASS/FAIL อยู่ที่ `docs/loadtest_report.md`
traffic mix = `/predict` 10 : `/predict_batch` (20 แถว) 1 : `/health` 1

| SLO (`configs/slo.yaml`) | เป้าหมาย | วัดจาก |
|---|---|---|
| Latency p50 | ≤ 50 ms | `/predict` ใน Locust |
| Latency p95 | ≤ 200 ms | `/predict` ใน Locust |
| Error rate | ≤ 1% | ทุก request ใน Locust |
| Availability | ≥ 99% | ทุก request ใน Locust (production: จาก Prometheus) |

## Metrics สำหรับ Monitoring

| Metric | ใช้ทำอะไร |
|---|---|
| `noshow_request_latency_seconds` (histogram, label `path`) | p50/p95 ใน Grafana: `histogram_quantile(0.95, sum by (le) (rate(noshow_request_latency_seconds_bucket{path="/predict"}[5m])))` |
| `noshow_requests_total` (label `path`, `method`, `status`) | error rate / availability |
| `noshow_predictions_total` (label `alert`) | ปริมาณการแจ้งเตือน |
| `noshow_prediction_score` (histogram) | การกระจายของ score (prediction drift) |
| `noshow_model_info` (label `version`, `threshold`) | version ที่ serve อยู่ |
