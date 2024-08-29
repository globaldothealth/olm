from pathlib import Path

import pytest
import pandas as pd

from obr.plots import (
    get_epicurve,
    get_delays,
    get_counts,
    get_age_bin_data,
    get_timeseries_location_status,
)
from obr.util import read_csv

DATA = read_csv(Path(__file__).with_name("test_data.csv"), date_columns=["Data_up_to"])

EXPECTED_TIMESERIES_LOCATION_STATUS = """Date_onset_estimated,daily_confirmed,daily_probable,cumulative_confirmed,cumulative_probable,Location_District
2023-02-06,0,1,0,1,Bata
2023-03-05,1,0,1,1,Bata
2023-01-13,0,1,0,1,Ebiebyin
2023-03-29,1,0,1,1,Ebiebyin
2023-01-05,1,0,1,0,Nsoc Nsomo
2023-02-19,1,0,2,0,Nsoc Nsomo
2023-02-11,1,0,1,0,Nsork
2023-01-05,1,0,1,0,Total
2023-01-13,0,1,1,1,Total
2023-02-06,0,1,1,2,Total
2023-02-11,1,0,2,2,Total
2023-02-19,1,0,3,2,Total
2023-03-05,1,0,4,2,Total
2023-03-29,1,0,5,2,Total
"""


@pytest.mark.parametrize(
    "column,expected_delay_series",
    [("Date_death", [4, 8, 6, 6]), ("Date_of_first_consult", [6, 4, 2])],
)
def test_get_delays(column, expected_delay_series):
    assert list(get_delays(DATA, column).dt.days) == expected_delay_series


def test_get_age_bin_data():
    expected = pd.DataFrame(
        [
            dict(Bin="0", Gender="male", N=1.0),
            dict(Bin="20-29", Gender="male", N=1.0),
            dict(Bin="50-59", Gender="female", N=1.0),
            dict(Bin="50-59", Gender="male", N=1.0),
            dict(Bin="80+", Gender="female", N=1.0),
        ]
    )
    assert get_age_bin_data(DATA).equals(expected)


def test_get_epicurve():
    epicurve = get_epicurve(
        DATA, "Date_onset", "Case_status", ["confirmed", "probable"]
    )
    assert (
        epicurve.to_csv()
        == """Date_onset,confirmed,probable
2023-01-05,1,0
2023-01-13,1,1
2023-02-06,1,2
2023-02-11,2,2
2023-02-19,3,2
2023-03-05,4,2
2023-03-29,5,2
"""
    )


def test_get_counts():
    assert get_counts(DATA, date_col="Data_up_to") == {
        "n_confirmed": 5,
        "n_probable": 2,
        "n_suspected": 0,
        "date": "2023-04-04",
        "pc_valid_age_gender": 100,
    }


def test_get_timeseries_location_status():
    data = DATA.rename(columns={"Date_onset": "Date_onset_estimated"})
    assert (
        get_timeseries_location_status(data).to_csv(index=False)
        == EXPECTED_TIMESERIES_LOCATION_STATUS
    )
