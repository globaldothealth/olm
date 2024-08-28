"""
Briefing report generator for Marburg 2023 outbreak
"""

import logging
import datetime
from pathlib import Path
from typing import Any, Callable
from functools import cache

import boto3
import chevron
import pandas as pd
import numpy as np
from dateutil.parser import ParserError
import plotly.graph_objects as go
import plotly.io
import plotly.express as px
from plotly.subplots import make_subplots

PlotFunction = Callable[..., dict[str, Any] | go.Figure]
PlotData = tuple[str, PlotFunction, dict[str, Any]]
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


def get_age_bins(age: str) -> range:
    "Returns age bin sequence range from age string in format start-end"

    if age == "0":
        return range(0, 1)
    if "-" in age:
        start_age, end_age = list(map(int, age.split("-")))
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


def render(template: Path, variables: dict[str, Any]) -> str:
    with template.open() as f:
        return chevron.render(f, variables)


def render_figure(fig, key: str) -> str:
    return {key: plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)}


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
                "CallerReference": f"obr_{datetime.datetime.now().isoformat()}",
            },
        )
        logging.info(f"Invalidation ID: {invalidation['Invalidation']['Id']}")
    except Exception:
        logging.info("Exception occurred when trying to invalidate existing cache")
        raise


def build(
    outbreak_name: str,
    data_url: str,
    plots: list[PlotData],
    output_bucket: str | None = None,
    cloudfront_distribution: str | None = None,
):
    "Build epidemiological report"
    assert " " not in outbreak_name, "Outbreak name should not have spaces"
    date = datetime.datetime.today().date()
    output_file = f"{outbreak_name}.html"
    if not (template := Path(__file__).parent / "outbreaks" / output_file).exists():
        raise FileNotFoundError(f"Template for outbreak not found at: {template}")
    var = {"published_date": str(date)}
    df = pd.read_csv(data_url, na_values=["NK", "N/K"])
    for plot in plots:
        kwargs = {} if len(plot) == 2 else plot[2]
        if plot[0] == "data":
            var.update(plot[1](df, **kwargs))
        else:
            assert plot[0].startswith("figure")
            var.update(
                render_figure(plot[1](df, **kwargs), plot[0].removeprefix("figure/"))
            )

    report_data = render(template, var)
    Path(output_file).write_text(report_data)

    if output_bucket:
        store_s3(
            report_data,
            [output_file, f"{outbreak_name}_{date}.html"],
            bucket_name=output_bucket,
            content_type="text/html",
        )
    if cloudfront_distribution:
        invalidate_cache(cloudfront_distribution)
