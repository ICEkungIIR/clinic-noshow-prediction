"""Pandera schema for the raw no-show data."""

import pandera.pandas as pa

RAW_SCHEMA = pa.DataFrameSchema(
    {
        "PatientId": pa.Column(float, pa.Check.gt(0)),
        "AppointmentID": pa.Column(int, unique=True),
        "Gender": pa.Column(str, pa.Check.isin(["F", "M"])),
        "ScheduledDay": pa.Column(str),
        "AppointmentDay": pa.Column(str),
        "Age": pa.Column(int, pa.Check.in_range(-1, 120)),
        "Neighbourhood": pa.Column(str),
        "Scholarship": pa.Column(int, pa.Check.isin([0, 1])),
        "Hipertension": pa.Column(int, pa.Check.isin([0, 1])),
        "Diabetes": pa.Column(int, pa.Check.isin([0, 1])),
        "Alcoholism": pa.Column(int, pa.Check.isin([0, 1])),
        "Handcap": pa.Column(int, pa.Check.in_range(0, 4)),
        "SMS_received": pa.Column(int, pa.Check.isin([0, 1])),
        "No-show": pa.Column(str, pa.Check.isin(["Yes", "No"])),
    },
    strict=True,  # no missing or extra columns
    coerce=True,  # convert types first (e.g. int PatientId -> float)
)
