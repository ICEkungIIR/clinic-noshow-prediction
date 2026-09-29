import pandas as pd
import pytest
from pandera.errors import SchemaError

from noshow.data.clean import clean
from noshow.data.schema import RAW_SCHEMA


def test_good_data_passes():
    df = pd.read_csv("tests/fixtures/good_data.csv")
    RAW_SCHEMA.validate(df)


def test_bad_data_fails():
    df = pd.read_csv("tests/fixtures/bad_data.csv")
    with pytest.raises(SchemaError):
        RAW_SCHEMA.validate(df)


def test_clean():
    df = clean(pd.read_csv("tests/fixtures/good_data.csv"))
    assert len(df) == 2
    assert df["Age"].min() >= 0
    assert df["Handcap"].max() <= 1
