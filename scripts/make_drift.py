import pandas as pd
import yaml

from noshow.data.clean import clean
from noshow.data.split import time_split

s = yaml.safe_load(open("configs/params.yaml"))["split"]
df = clean(pd.read_csv("data/raw/noshow.csv"))
train, val, test = time_split(df, s["train_end"], s["val_end"])

# ข้อมูลอ้างอิง: ข้อมูล train ที่โมเดลใช้เรียนรู้
train.to_csv("data/processed/reference.csv", index=False)

# Data drift: features เปลี่ยน (ผู้ป่วยแก่ขึ้น 20 ปี, ทุกคนได้ SMS)
data_drift = test.copy()
data_drift["Age"] = (data_drift["Age"] + 20).clip(upper=115)
data_drift["SMS_received"] = 1
data_drift.to_csv("data/processed/data_drift.csv", index=False)

# Concept drift: features เหมือนเดิม แต่คนที่ได้ SMS ไม่มาทั้งหมด
concept_drift = test.copy()
got_sms = concept_drift["SMS_received"] == 1
concept_drift.loc[got_sms, "No-show"] = "Yes"
concept_drift.to_csv("data/processed/concept_drift.csv", index=False)

print(
    "reference:", len(train), "data_drift:", len(data_drift), "concept_drift:", len(concept_drift)
)
