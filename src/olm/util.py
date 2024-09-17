"""
Briefing report generator for Marburg 2023 outbreak
"""

import re
import logging
import datetime
from typing import Callable

import boto3
import pandas as pd


pd.options.mode.chained_assignment = None

AGE_BINS = [
    (0, 0),
    (1, 9),
    (10, 19),
    (20, 29),
    (30, 39),
    (40, 49),
    (50, 59),
    (60, 69),
    (70, 79),
    (80, 120),
]
REGEX_DATE = r"^202\d-[0,1]\d-[0-3]\d"

# Upper bounded ages below this are upper bounded to 60 Example: an age
# of '>15' would be mapped to 15-60 while an age of '>70' would be
# mapped to 70-120
SENIOR_AGE = 60

# Very few humans reach this age, ages above are probably data entry
# errors
UPPER_LIMIT_AGE = 120


def non_null_unique(arr: pd.Series) -> pd.Series:
    uniq = arr.unique()
    return uniq[~pd.isna(uniq)]


def msg_ok(module: str, s: str):
    print(f"\033[0;32m✓ olm[{module}]\t\033[0m {s}")


def msg_fail(module: str, s: str):
    print(f"\033[0;31m✗ olm[{module}]\t\033[0m {s}")


def rename_columns(columns: dict[str, str]) -> Callable[[pd.DataFrame], pd.DataFrame]:
    def rename_table(df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=columns)

    return rename_table


def bold_brackets(s: str) -> str:
    """Given a text with brackets such as [this], renders it in bold font"""
    return s.replace("[", "\033[1m").replace("]", "\033[0m")


def sort_values(
    by: list[str], ascending: bool
) -> Callable[[pd.DataFrame], pd.DataFrame]:
    def sort_table(df: pd.DataFrame) -> pd.DataFrame:
        return df.sort_values(by=by, ascending=ascending)

    return sort_table


def fix_datetimes(df: pd.DataFrame, additional_date_columns: list[str] = []):
    "Convert date fields to datetime in place"
    date_columns = [
        c for c in df.columns if c.startswith("Date_") or "Date " in c
    ] + additional_date_columns
    for date_col in date_columns:
        df[date_col] = df[date_col].map(
            lambda x: (
                pd.to_datetime(x)
                if isinstance(x, str) and re.match(REGEX_DATE, x)
                else None
            )
        )


def get_age_bins(age: str) -> range:
    "Returns age bin sequence range from age string in format start-end"

    if age == "0":
        return range(0, 1)
    if "-" in age:
        start_age, end_age = list(map(int, age.split("-")))
    elif ">" in age:
        start_age = int(age.replace(">", ""))
        end_age = UPPER_LIMIT_AGE if start_age >= SENIOR_AGE else SENIOR_AGE
    else:
        start_age = end_age = int(age)
    for i in range(len(AGE_BINS)):
        start_bin, end_bin = AGE_BINS[i]
        if start_bin <= start_age <= end_bin:
            start_index = i
        if start_bin <= end_age <= end_bin:
            end_index = i
    return range(start_index, end_index + 1)


def name_bin(bin_idx: int) -> str:
    bin = AGE_BINS[bin_idx]
    if bin[0] == bin[1]:
        return str(bin[0])
    if bin[0] == 80:
        return "80+"
    return f"{bin[0]}-{bin[1]}"


def percentage_occurrence(df: pd.DataFrame, filter_series: pd.Series) -> int:
    """Returns percentage occurrence of filter_series within a dataframe"""
    return int(round(100 * sum(filter_series) / len(df)))


def store_s3(
    data: str,
    key: str | list[str],
    bucket_name: str,
    content_type: str,
):
    keys = [key] if isinstance(key, str) else key
    for k in keys:
        logging.info(f"Uploading data to s3://{bucket_name}/{k}")
        try:
            boto3.resource("s3").Object(bucket_name, k).put(
                Body=data, ContentType=content_type
            )
        except Exception:
            logging.exception("An exception occurred while trying to upload files")
            raise


def invalidate_cache(
    distribution_id: str,
    paths: list[str],
):
    "Invalidates CloudFront cache"
    try:
        invalidation = boto3.client("cloudfront").create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": len(paths), "Items": paths},
                "CallerReference": f"olm_report_{datetime.datetime.now().isoformat()}",
            },
        )
        logging.info(f"Invalidation ID: {invalidation['Invalidation']['Id']}")
    except Exception:
        logging.info("Exception occurred when trying to invalidate existing cache")
        raise


def read_csv(
    filename: str, additional_date_columns: list[str] = [], convert_dates: bool = True
) -> pd.DataFrame:
    """Helper function with post-processing steps after pd.read_csv

    Parameters
    ----------
    filename
        File or URL to read from. This is passed to pd.read_csv() so any URL
        supported by pandas is supported here
    date_columns
        Additional date columns that should be converted. By default read_csv
        fixes date columns to be of the correct type if they start with 'Date_'
        or have 'Date ' in their column name
    """
    df = pd.read_csv(filename, dtype=str, na_values=["N/K", "NK"])
    if convert_dates:
        fix_datetimes(df, additional_date_columns)
    return df
