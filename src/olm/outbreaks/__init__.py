"""
Outbreak configurations
"""

import json
from pathlib import Path
from typing import Any

import requests
import pandas as pd
from ..plots import (
    get_counts,
    get_aggregate,
    get_countries_with_status,
    get_countries_with_anyof_statuses,
    plot_epicurve,
    plot_timeseries_location_status,
    plot_age_gender,
    plot_delay_distribution,
)
from ..types import OutbreakInfo
from ..util import read_csv
from ..sources import source_databutton


outbreak_marburg = [
    ("data", get_counts, {"date_col": "Data_up_to"}),
    (
        "figure/epicurve",
        plot_epicurve,
        {
            "title": "Date of symptom onset",
            "date_col": "Date_onset_estimated",
            "groupby_col": "Case_status",
        },
    ),
    (
        "figure/epicurve_location_status",
        plot_timeseries_location_status,
        {"admin_column": "Location_District"},
    ),
    ("figure/age_gender", plot_age_gender),
    (
        "figure/delay_distribution_consult",
        plot_delay_distribution,
        {
            "col": "Date_of_first_consult",
            "title": "Delay to consultation from onset",
            "index": "A",
            "max_delay_days": 20,
        },
    ),
    (
        "figure/delay_distribution_death",
        plot_delay_distribution,
        {
            "col": "Date_death",
            "title": "Delay to death from onset",
            "index": "B",
            "max_delay_days": 20,
        },
    ),
]

outbreak_mpox_2024 = [
    ("data", get_counts, {"date_col": "Date_entry"}),
    (
        "table/clades",
        source_databutton,
        {
            "link": "https://worldhealthorg.shinyapps.io/mpx_global/",
            "button_text": "Download MPXV clades",
        },
    ),
    (
        "table/aggregate",
        get_aggregate,
        {
            "country_col": "Location_Admin0",
            "columns": [("Case_status", "confirmed"), ("Outcome", "death")],
        },
    ),
    (
        "data",
        get_countries_with_status,
        {"country_col": "Location_Admin0", "statuses": ["confirmed", "suspected"]},
    ),
    (
        "data",
        get_countries_with_anyof_statuses,
        {"country_col": "Location_Admin0", "statuses": ["confirmed", "suspected"]},
    ),
    (
        "figure/epicurve_source_report",
        plot_epicurve,
        {
            "title": "Date of report in primary source",
            "date_col": "Date_report_source_I",
            "groupby_col": "Case_status",
            "values": ["confirmed", "suspected"],
        },
    ),
    (
        "figure/epicurve_confirmed",
        plot_epicurve,
        {
            "title": "Date of case confirmation",
            "date_col": "Date_confirmation",
            "groupby_col": "Case_status",
            "values": ["confirmed"],
        },
    ),
    ("figure/age_gender", plot_age_gender),
]

OUTBREAKS: dict[str, OutbreakInfo] = {
    "marburg": {
        "id": "GHL2023.D11.1D60.1",
        "description": "Marburg 2023 Equatorial Guinea",
        "plots": outbreak_marburg,
        "additional_date_columns": ["Data_up_to"],
    },
    "mpox-2024": {
        "id": "GHL2024.D11.1E71",
        "description": "Mpox 2024",
        "plots": outbreak_mpox_2024,
        "url": "https://mpox-2024.s3.eu-central-1.amazonaws.com/latest.csv",
        "schema": "GHL2024.D11.1E71.schema.json",
    },
}


def get_schema_url(outbreak: str) -> str | None:
    return OUTBREAKS[outbreak].get("schema")


def read_schema(schema: str | Path) -> dict[str, Any]:
    "Reads schema from outbreak"
    if isinstance(schema, str) and schema.startswith("http"):
        if (res := requests.get(schema)).status_code == 200:
            return res.json()
    else:
        return json.loads(Path(schema).read_text())


def read_outbreak(
    outbreak: str, data_url: str | None = None, convert_dates: bool = True
) -> pd.DataFrame:
    assert outbreak in OUTBREAKS, f"Outbreak {outbreak} not found"
    if data_url is None and OUTBREAKS[outbreak].get("url") is None:
        raise ValueError(
            f"Either data_url should be specified or the url key should exist for outbreak: {outbreak}"
        )
    return read_csv(
        data_url or OUTBREAKS[outbreak]["url"],
        additional_date_columns=OUTBREAKS[outbreak].get("additional_date_columns", []),
        convert_dates=convert_dates,
    )


__all__ = ["OUTBREAKS"]
