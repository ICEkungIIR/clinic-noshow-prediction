"""Exploratory data analysis of the raw no-show dataset.

Prints the findings and writes them to docs/eda.md (used in the report).
Usage: uv run python scripts/eda.py
"""

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "params.yaml"
OUT = ROOT / "docs" / "eda.md"


def pct(n: int, total: int) -> str:
    return f"{n:,} ({n / total:.2%})"


def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text())
    df = pd.read_csv(ROOT / cfg["data"]["raw_path"])
    target = cfg["target"]["column"]
    n = len(df)
    lines: list[str] = ["# EDA: Medical Appointment No Shows (raw data)", ""]

    def section(title: str, body: str) -> None:
        lines.extend([f"## {title}", "", body, ""])

    # 1. Size and dtypes
    section(
        "1. ขนาดและชนิดข้อมูล",
        f"- จำนวนแถว: **{n:,}**, จำนวนคอลัมน์: **{df.shape[1]}**\n\n"
        "```\n" + df.dtypes.to_string() + "\n```",
    )

    # 2. Target balance
    counts = df[target].value_counts()
    section(
        "2. สัดส่วน No-show (target)",
        "\n".join(f"- `{k}`: {pct(v, n)}" for k, v in counts.items()),
    )

    # 3. Time range
    sched = pd.to_datetime(df["ScheduledDay"])
    appt = pd.to_datetime(df["AppointmentDay"])
    per_day = df.assign(day=appt.dt.date).groupby("day")[target].agg(
        n="size", noshow_rate=lambda s: (s == cfg["target"]["positive_label"]).mean()
    )
    section(
        "3. ช่วงเวลา",
        f"- ScheduledDay: {sched.min()} → {sched.max()}\n"
        f"- AppointmentDay: {appt.min().date()} → {appt.max().date()} "
        f"({per_day.shape[0]} วันที่มีนัด)\n\n"
        "จำนวนนัดและอัตรา no-show ต่อวัน (AppointmentDay):\n\n"
        "```\n" + per_day.round(3).to_string() + "\n```",
    )

    # 4. Missing values and duplicates
    content_cols = [c for c in df.columns if c != "AppointmentID"]
    section(
        "4. ค่าว่างและข้อมูลซ้ำ",
        f"- ค่าว่างทั้งหมด: {int(df.isna().sum().sum())}\n"
        f"- แถวซ้ำทั้งแถว: {int(df.duplicated().sum())}\n"
        f"- AppointmentID ซ้ำ: {int(df['AppointmentID'].duplicated().sum())}\n"
        f"- แถวที่เนื้อหาซ้ำกัน (ยกเว้น AppointmentID): "
        f"{int(df.duplicated(subset=content_cols).sum()):,}",
    )

    # 5. Patients with multiple appointments
    per_patient = df.groupby("PatientId").size()
    multi = per_patient[per_patient > 1]
    section(
        "5. PatientId ที่นัดหลายครั้ง",
        f"- จำนวนผู้ป่วยไม่ซ้ำ: {per_patient.size:,}\n"
        f"- ผู้ป่วยที่นัด > 1 ครั้ง: {pct(multi.size, per_patient.size)} "
        f"ครอบคลุม {pct(int(multi.sum()), n)} ของนัดทั้งหมด\n"
        f"- จำนวนนัดสูงสุดต่อคน: {per_patient.max()}\n"
        f"- PatientId ที่ไม่ใช่จำนวนเต็ม: {int((df['PatientId'] % 1 != 0).sum())}",
    )

    # 6. Data quality issues to clean
    lead_days = (appt - sched.dt.normalize()).dt.days
    section(
        "6. ปัญหาคุณภาพข้อมูล (ต้อง clean)",
        f"- Age < 0: {int((df['Age'] < 0).sum())} แถว, "
        f"Age > 100: {int((df['Age'] > 100).sum())} แถว "
        f"(min={df['Age'].min()}, max={df['Age'].max()})\n"
        f"- Handcap: {df['Handcap'].value_counts().sort_index().to_dict()} "
        "(ควรเป็น 0/1 แต่มีค่า 2–4)\n"
        f"- ScheduledDay (วันที่) หลัง AppointmentDay: {int((lead_days < 0).sum())} แถว\n"
        f"- นัดวันเดียวกัน (lead = 0 วัน): {pct(int((lead_days == 0).sum()), n)}\n"
        f"- Gender: {df['Gender'].value_counts().to_dict()}\n"
        f"- Neighbourhood: {df['Neighbourhood'].nunique()} ค่า",
    )

    # 7. Candidate split boundaries from params.yaml
    s = cfg["split"]
    d = appt.dt.normalize()
    train = d <= s["train_end"]
    val = (d > s["train_end"]) & (d <= s["val_end"])
    test = d > s["val_end"]
    ids = {k: set(df.loc[m, "PatientId"]) for k, m in [("train", train), ("val", val), ("test", test)]}
    section(
        "7. Time-based split ตาม params.yaml",
        f"- train (≤ {s['train_end']}): {pct(int(train.sum()), n)}\n"
        f"- val ({s['train_end']} < d ≤ {s['val_end']}): {pct(int(val.sum()), n)}\n"
        f"- test (> {s['val_end']}): {pct(int(test.sum()), n)}\n"
        f"- PatientId ซ้ำ train∩val: {len(ids['train'] & ids['val']):,}, "
        f"train∩test: {len(ids['train'] & ids['test']):,}, "
        f"val∩test: {len(ids['val'] & ids['test']):,}",
    )

    text = "\n".join(lines)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nwritten to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
