from pathlib import Path

import pytest
import pandas as pd

from olm.plots import (
    get_epicurve,
    get_aggregate,
    get_delays,
    get_counts,
    get_age_bin_data,
    get_timeseries_location_status,
    get_countries_with_status,
    get_countries_with_anyof_statuses,
    get_trailing_case_count
)
from olm.util import read_csv

DATA = read_csv(
    Path(__file__).with_name("test_data.csv"), additional_date_columns=["Data_up_to"]
)
STATUS_DATA = read_csv(Path(__file__).with_name("test_status_data.csv"))

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
    "target_column,expected_delay_series,onset_column",
    [("Date_death", [4, 8, 6, 6], 'Date_onset'), ("Date_of_first_consult", [6, 4, 2], 'Date_onset')],
)
def test_get_delays(target_column, expected_delay_series, onset_column):
    assert list(get_delays(DATA, target_column, onset_column).dt.days) == expected_delay_series


def test_aggregate():
    assert get_aggregate(
        DATA, "Country", [("Case_status", "confirmed"), ("Outcome", "death")]
    ).equals(
        pd.DataFrame({"Country": ["A", "B"], "confirmed": [2, 3], "death": [2, 2]})
    )


def test_get_countries_with_anyof_statuses():
    assert get_countries_with_anyof_statuses(
        STATUS_DATA, "Country", ["confirmed", "suspected"]
    ) == {"n_countries_confirmed_or_suspected": 3}


def test_get_countries_with_status():
    assert get_countries_with_status(
        STATUS_DATA, "Country", ["confirmed", "suspected", "probable"]
    ) == {
               "n_countries_confirmed": 2,
               "n_countries_confirmed_only": 1,
               "n_countries_probable": 1,
               "n_countries_probable_only": 1,
               "n_countries_suspected": 2,
               "n_countries_suspected_only": 1,
           }


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
        "n_dead": 4,
    }


def test_get_timeseries_location_status():
    data = DATA.rename(columns={"Date_onset": "Date_onset_estimated"})
    assert (
            get_timeseries_location_status(data).to_csv(index=False)
            == EXPECTED_TIMESERIES_LOCATION_STATUS
    )


def test_get_trailing_case_count():
    assert get_trailing_case_count(DATA, date_col="Date_onset", trailing_time_in_days=7) == {
        '2023-01-05': 1,
        '2023-01-06': 1,
        '2023-01-07': 1,
        '2023-01-08': 1,
        '2023-01-09': 1,
        '2023-01-10': 1,
        '2023-01-11': 1,
        '2023-01-13': 1,
        '2023-01-14': 1,
        '2023-01-15': 1,
        '2023-01-16': 1,
        '2023-01-17': 1,
        '2023-01-18': 1,
        '2023-01-19': 1,
        '2023-02-06': 1,
        '2023-02-07': 1,
        '2023-02-08': 1,
        '2023-02-09': 1,
        '2023-02-10': 1,
        '2023-02-11': 2,
        '2023-02-12': 2,
        '2023-02-13': 1,
        '2023-02-14': 1,
        '2023-02-15': 1,
        '2023-02-16': 1,
        '2023-02-17': 1,
        '2023-02-19': 1,
        '2023-02-20': 1,
        '2023-02-21': 1,
        '2023-02-22': 1,
        '2023-02-23': 1,
        '2023-02-24': 1,
        '2023-02-25': 1,
        '2023-03-05': 1,
        '2023-03-06': 1,
        '2023-03-07': 1,
        '2023-03-08': 1,
        '2023-03-09': 1,
        '2023-03-10': 1,
        '2023-03-11': 1,
        '2023-03-29': 1,
        '2023-03-30': 1,
        '2023-03-31': 1,
        '2023-04-01': 1,
        '2023-04-02': 1,
        '2023-04-03': 1,
        '2023-04-04': 1
    }
