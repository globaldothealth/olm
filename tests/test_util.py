from pathlib import Path

import pytest

from olm.util import get_age_bins, name_bin, read_csv

DATA = read_csv(Path(__file__).with_name("test_data.csv"))


@pytest.mark.parametrize(
    "age,expected_range",
    [
        ("50-55", range(6, 7)),
        ("0", range(0, 1)),
        ("65", range(7, 8)),
        (">15", range(2, 8)),
        (">75", range(8, 10)),
    ],
)
def test_get_age_bins(age, expected_range):
    "Returns age bin sequence range from age string in format start-end"
    assert get_age_bins(age) == expected_range


@pytest.mark.parametrize("bin_idx,expected", [(0, "0"), (1, "1-9"), (9, "80+")])
def test_name_bin(bin_idx, expected):
    assert name_bin(bin_idx) == expected
