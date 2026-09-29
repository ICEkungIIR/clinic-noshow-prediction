"""EDA of the raw no-show dataset. Usage: uv run python scripts/eda.py"""

import pandas as pd
import yaml

from noshow.data.split import patient_overlap, time_split

df = pd.read_csv("data/raw/noshow.csv")

print("=== 1. Size ===")
print("rows:", len(df), "columns:", len(df.columns))
print(df.dtypes)

print("\n=== 2. No-show ===")
print(df["No-show"].value_counts())
print(df["No-show"].value_counts(normalize=True))

print("\n=== 3. Time range ===")
df["ScheduledDay"] = pd.to_datetime(df["ScheduledDay"])
df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"])
print("ScheduledDay:", df["ScheduledDay"].min(), "to", df["ScheduledDay"].max())
print("AppointmentDay:", df["AppointmentDay"].min(), "to", df["AppointmentDay"].max())
print(df["AppointmentDay"].value_counts().sort_index())

print("\n=== 4. Missing / duplicates ===")
print("missing values:", df.isna().sum().sum())
print("duplicate rows:", df.duplicated().sum())
print("duplicate AppointmentID:", df["AppointmentID"].duplicated().sum())

print("\n=== 5. Patients ===")
visits = df["PatientId"].value_counts()
print("unique patients:", len(visits))
print("patients with > 1 appointment:", (visits > 1).sum())
print("max appointments per patient:", visits.max())
print("non-integer PatientId:", (df["PatientId"] % 1 != 0).sum())

print("\n=== 6. Data quality ===")
print("Age < 0:", (df["Age"] < 0).sum())
print("Age > 100:", (df["Age"] > 100).sum())
print("Handcap values:")
print(df["Handcap"].value_counts())
late = df["ScheduledDay"].dt.normalize() > df["AppointmentDay"]
print("ScheduledDay after AppointmentDay:", late.sum())

print("\n=== 7. Split ===")
s = yaml.safe_load(open("configs/params.yaml"))["split"]
train, val, test = time_split(df, s["train_end"], s["val_end"])
print("train:", len(train), "val:", len(val), "test:", len(test))
print("patient overlap:", patient_overlap(train, val, test))
