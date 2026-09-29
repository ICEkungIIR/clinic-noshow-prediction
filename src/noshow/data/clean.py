import pandas as pd


def clean(df):
    df = df.copy()
    df["ScheduledDay"] = pd.to_datetime(df["ScheduledDay"])
    df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"])

    df = df[df["Age"] >= 0]
    df = df[df["ScheduledDay"].dt.normalize() <= df["AppointmentDay"]]
    df["Handcap"] = df["Handcap"].clip(upper=1)
    return df.reset_index(drop=True)
