# Real-Time Urban Complaint Triage System
ระบบจำแนกและจัดลำดับความเร่งด่วนของเรื่องร้องเรียนเมืองแบบเรียลไทม์ (Traffy Fondue Open Data)

โครงงานรายวิชา **CP413008 Machine Learning Engineering for Production** ภาคเรียนที่ 1/2569 มหาวิทยาลัยขอนแก่น

## สมาชิกและความรับผิดชอบ

| # | รหัสนักศึกษา | ชื่อ-นามสกุล | Sec | Workstream |
|---|---|---|---|---|
| 1 | 673380078-7 | นายธันว์ สว่างศรี | 2 | Serving (FastAPI), Docker, Load test, SLO |
| 2 | 673380526-6 | นายพีรพงษ์ ทองฤทธิ์ | 2 | Pipeline orchestration (Prefect DAG) |
| 3 | 673380306-0 | นายกิตตินันท์ ไขไพรวัน | 1 | Data ingestion, split, validation |
| 4 | 673380532-1 | นายศรัณยู เจริญผล | 1 | Tech lead / Integration, Modeling |
| 5 | 673380075-3 | นายฑีฌานนท์ อัศวะภูมิ | 2 | Monitoring, drift, retraining |
| 6 | 673380528-2 | นายภูรินทร์ ศรีฐาน | 1 | CI/CD, model gate, registry, rollback |
| 7 | 673380313-3 | นายณันทพงศ์ พยัคมะเริง | 2 | Urgency labeling, AI Project Canvas, report |

## Quickstart (จากเครื่องเปล่า)

ต้องมี [uv](https://docs.astral.sh/uv/) และ Docker

```bash
git clone <repo-url> && cd urban-complaint-triage
make setup      # ติดตั้ง Python 3.11 + dependencies ตาม uv.lock (เวอร์ชันล็อกทุกตัว)
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

## Git workflow

- ห้าม push ตรงเข้า `main` ทุกงานทำผ่าน branch แล้วเปิด Pull Request
- ตั้งชื่อ branch: `feat/<ชื่อ>-<เรื่อง>` เช่น `feat/kittinan-pandera-schema`, แก้บั๊กใช้ `fix/...`
- PR ต้องผ่าน CI และมีคน approve อย่างน้อย 1 คนก่อน merge
- ก่อนเปิด PR ให้รัน `make format && make test`

## Environment

- Python 3.11, dependencies ล็อกเวอร์ชันใน `uv.lock` (ห้ามแก้มือ ให้ใช้ `uv add <pkg>` แล้ว commit lock ด้วย)
- WangchanBERTa (การทดลองรอบ 3): `uv sync --extra bert`
- ข้อมูลไม่เก็บใน git ให้ใช้ `scripts/download_data.py` (ตรวจ SHA-256 เพื่อยืนยันเวอร์ชันข้อมูล)

## โครงสร้าง

```
src/triage/
  data/        ingest, time-based split, Pandera validation
  features/    preprocessing ชุดเดียว ใช้ทั้ง train และ serve (กัน training-serving skew)
  models/      train, evaluate, gate, MLflow registry
  serving/     FastAPI app
  monitoring/  Evidently drift + retrain trigger
  pipeline/    Prefect flows (DAG)
configs/       params.yaml, slo.yaml
docker/        Dockerfiles
monitoring/    Prometheus / Grafana config
scripts/       download_data.py, replay_stream.py
tests/         unit + data tests
```

## การใช้เครื่องมือ AI

ระบุส่วนที่ใช้ AI ช่วยเขียนโค้ดไว้ในรายงาน (ตามข้อกำหนดรายวิชา) และทุกคนต้องอธิบายโค้ดที่ตนเอง commit ได้
