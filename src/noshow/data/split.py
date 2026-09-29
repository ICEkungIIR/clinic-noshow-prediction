def time_split(df, train_end, val_end):
    day = df["AppointmentDay"]
    train = df[day <= train_end]
    val = df[(day > train_end) & (day <= val_end)]
    test = df[day > val_end]
    return train, val, test


def patient_overlap(train, val, test):
    tr = set(train["PatientId"])
    va = set(val["PatientId"])
    te = set(test["PatientId"])
    return {
        "train_val": len(tr & va),
        "train_test": len(tr & te),
        "val_test": len(va & te),
    }
