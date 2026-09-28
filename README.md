# Clinic Appointment No-Show Prediction
ระบบทำนายผู้ป่วยที่ไม่มาตามนัดของคลินิก เพื่อให้คลินิกส่ง SMS/โทรเตือน หรือจัด overbooking ได้ทันเวลา
(ชุดข้อมูล [Medical Appointment No Shows](https://www.kaggle.com/datasets/joniarroba/noshowappointments), 110,527 นัดหมาย)

โครงงานรายวิชา **CP413008 Machine Learning Engineering for Production** ภาคเรียนที่ 1/2569 มหาวิทยาลัยขอนแก่น

## สมาชิกและความรับผิดชอบ

| # | รหัสนักศึกษา | ชื่อ-นามสกุล | Sec | Workstream |
|---|---|---|---|---|
| 1 | 673380078-7 | นายธันว์ สว่างศรี | 2 | Serving (FastAPI real-time + batch), Docker, Load test p50/p95, SLO |
| 2 | 673380526-6 | นายพีรพงษ์ ทองฤทธิ์ | 2 | Pipeline orchestration (Prefect DAG, `make pipeline`) |
| 3 | 673380306-0 | นายกิตตินันท์ ไขไพรวัน | 1 | Data ingestion, time-based split, Pandera schema, bad-data demo |
| 4 | 673380532-1 | นายศรัณยู เจริญผล | 1 | Tech lead / Integration, Features (shared preprocessing), Modeling + MLflow tracking |
| 5 | 673380075-3 | นายฑีฌานนท์ อัศวะภูมิ | 2 | Monitoring (Evidently data/concept drift, Grafana), retraining policy |
| 6 | 673380528-2 | นายภูรินทร์ ศรีฐาน | 1 | CI/CD (3 checks), model gate, registry, rollback |
| 7 | 673380313-3 | นายณันทพงศ์ พยัคมะเริง | 2 | AI Project Canvas, metrics ↔ business KPI, architecture diagram, report |

## Quickstart (จากเครื่องเปล่า)

ต้องมี [uv](https://docs.astral.sh/uv/), Docker และ Kaggle account
(ตั้ง `~/.kaggle/kaggle.json` หรือ env `KAGGLE_USERNAME` / `KAGGLE_KEY` หากดาวน์โหลดแบบไม่ login ไม่ได้)

```bash
git clone https://github.com/ICEkungIIR/urban-complaint-triage.git && cd urban-complaint-triage
make setup      # ติดตั้ง Python 3.11 + dependencies ตาม uv.lock (ล็อกเวอร์ชันทุกตัว)
make data       # ดาวน์โหลดข้อมูล -> data/raw/noshow.csv และพิมพ์ SHA-256 (= data version)
make test       # ruff + pytest
make up         # เปิด API, MLflow, Prefect, Prometheus, Grafana
curl localhost:8000/health
```

| Service | URL |
|---|---|
| API (FastAPI docs) | http://localhost:8000/docs |
| MLflow | http://localhost:5001 |
| Prefect | http://localhost:4200 |
| Prometheus | http://localhost:9090 |
| Grafana (admin/admin) | http://localhost:3000 |

## ข้อตกลงหลักของทีม

- **Target:** `No-show == "Yes"` → 1 (ผู้ป่วยไม่มา) ประมาณ 20% ของข้อมูล
- **Split:** ตามเวลา `AppointmentDay` (ดู `configs/params.yaml`) ห้ามสุ่ม
- **Optimizing metric:** PR-AUC ของคลาส no-show; **Gating:** ดู `configs/slo.yaml`
- **Preprocessing:** โค้ดชุดเดียวใน `src/noshow/features/` ใช้ทั้งตอน train และ serve
- **Registry model name:** `clinic-noshow`

## Git workflow

- ห้าม push ตรงเข้า `main` ทุกงานทำผ่าน branch แล้วเปิด Pull Request
- ตั้งชื่อ branch: `feat/<ชื่อ>-<เรื่อง>` เช่น `feat/kittinan-pandera-schema`, แก้บั๊กใช้ `fix/...`
- PR ต้องผ่าน CI และมีคน approve อย่างน้อย 1 คนก่อน merge
- ก่อนเปิด PR ให้รัน `make format && make test`
- คะแนนรายบุคคลดูจาก commit history — ทุกคน commit งานของตัวเองด้วย account ตัวเอง

## โครงสร้าง

```
src/noshow/
  data/        ingest, time-based split, Pandera validation
  features/    preprocessing ชุดเดียว ใช้ทั้ง train และ serve (กัน training-serving skew)
  models/      train, evaluate, gate
  registry/    MLflow registry: promote, rollback
  serving/     FastAPI app (/predict, /predict_batch, /health, /metrics)
  monitoring/  Evidently drift + retrain trigger
  pipeline/    Prefect flows (DAG)
configs/       params.yaml, slo.yaml
docker/        Dockerfiles
monitoring/    Prometheus / Grafana config
scripts/       download_data.py
tests/         unit + data tests
docs/          canvas, architecture, report
```

## การใช้เครื่องมือ AI

ระบุส่วนที่ใช้ AI ช่วยเขียนโค้ดไว้ในรายงาน (ตามข้อกำหนดรายวิชา) และทุกคนต้องอธิบายโค้ดที่ตนเอง commit ได้
