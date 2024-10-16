"""
Outbreak configurations
"""

import json
import datetime
from pathlib import Path

import chevron
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

import plotly.io
import fastjsonschema
from ..util import (
    read_csv,
    read_yaml,
    store_s3,
    invalidate_cache,
    msg_ok,
    rename_columns,
)
from ..types import LintResult, RowError
from ..sources import source_databutton, source_google_sheet
from .mpox2024 import mpox_2024_aggregate


OUTBREAK_SPECIFIC_METHODS = [mpox_2024_aggregate]
ALLOWED_METHODS = OUTBREAK_SPECIFIC_METHODS + [
    get_counts,
    get_aggregate,
    get_countries_with_status,
    get_countries_with_anyof_statuses,
    plot_epicurve,
    plot_timeseries_location_status,
    plot_age_gender,
    plot_delay_distribution,
    # sources -------------------
    source_databutton,
    source_google_sheet,
    # post processors -----------
    rename_columns,
]

OUTBREAKS_PATH = Path(__file__).parents[3] / "outbreaks"
OUTBREAKS = [f.stem for f in OUTBREAKS_PATH.glob("*.yml")]
TEMPLATES = OUTBREAKS_PATH / "templates"
HEADER = (TEMPLATES / "_header.html").read_text()
FOOTER = (TEMPLATES / "_footer.html").read_text()

TABLE_POSTPROCESSORS = {"rename_columns"}
REQUIRED_OUTBREAK_ATTRIBUTES = {"id", "description", "name"}
METHOD = {f.__name__: f for f in ALLOWED_METHODS}


def render_figure(fig, key: str) -> str:
    return {key: plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)}


def get_plot_method(key: str) -> str | None:
    "Preset mappings of figure keys to plot methods"
    if key.startswith("figure/epicurve"):
        return "plot_epicurve"
    if key == "figure/age_gender":
        return "plot_age_gender"
    return None


class Outbreak:
    def __init__(self, config: str, url: str | None = None):
        self.metadata = read_yaml(config)
        assert (
            REQUIRED_OUTBREAK_ATTRIBUTES <= set(self.metadata.keys())
        ), f"All required attributes not present in YAML file: {REQUIRED_OUTBREAK_ATTRIBUTES}"
        self.schema = None
        self.name = Path(config).stem
        assert " " not in self.name, "Outbreak name should not have spaces"

        self.schema_url = self.metadata.get("schema")
        self.additional_date_columns = self.metadata.get("additional_date_columns", [])
        self.url = self.metadata.get("url")
        self.plots = self.metadata.get("plots", {})
        if isinstance(self.schema_url, str):
            if (
                self.schema_url.startswith("http")
                and (res := requests.get(self.schema_url)).status_code == 200
            ):
                self.schema = res.json()
            else:
                self.schema = json.loads(Path(self.schema_url).read_text())
        if url:
            self.url = url
        if self.url:
            self.data = self.read(url)

    def read(
        self, data_url: str | None = None, convert_dates: bool = True
    ) -> pd.DataFrame:
        "Loads outbreak data from URL or path"
        data_url = data_url or self.url
        if data_url is None:
            raise ValueError(
                f"Either data_url should be specified or the url key should exist for outbreak: {self.name}"
            )

        return read_csv(
            data_url,
            additional_date_columns=self.additional_date_columns,
            convert_dates=convert_dates,
        )

    def lint(self, ignore_fields: list[str] = []) -> LintResult:
        errors: list[RowError] = []
        if not self.schema:
            raise ValueError("No schema supplied for outbreak in configuration")
        # do not convert dates as fastjsonschema will check date string representation
        df = self.read(convert_dates=False)
        validator = fastjsonschema.compile(self.schema)

        for row in df.to_dict("records"):
            id = row["ID"]
            nrow = {
                k: v for k, v in row.items() if pd.notnull(v) and k not in ignore_fields
            }
            try:
                validator(nrow)
            except fastjsonschema.JsonSchemaValueException as e:
                column = e.path[1]
                errors.append(RowError(id, column, nrow[column], e.message))
        return LintResult(self.name, str(self.schema_url), len(errors) == 0, errors)

    def make_report(
        self,
        output_bucket: str | None = None,
        cloudfront_distribution: str | None = None,
    ):
        """Build epidemiological report

        Parameters
        ----------
        output_bucket
            Output S3 bucket to write result to, in addition to local HTML output
            to {outbreak_name}.html
        cloudfront_distribution
            If specified, invalidates the cache for the cloudfront distribution
            without which changes are not made available
        """
        date = datetime.datetime.today().date()
        output_file = f"{self.name}.html"
        if not (template := TEMPLATES / output_file).exists():
            raise FileNotFoundError(f"Template for outbreak not found at: {template}")
        template_text = HEADER + template.read_text() + FOOTER
        if self.url is None:
            raise ValueError("No data url specified")
        var = {
            "name": self.name,
            "description": self.metadata["description"],
            "id": self.metadata["id"],
            "published_date": str(date),
            "data_url": self.metadata.get("url", ""),
        }
        df = read_csv(self.url, self.metadata.get("additional_date_columns", []))
        for plot in self.plots:
            plot_type, plot_key, *plot_info = plot.split("/")
            kwargs = self.plots[plot]
            if kwargs is None:
                kwargs = {}
            match plot_type:
                case "data":
                    var.update(METHOD[plot_key](df, **kwargs))
                case "table":
                    if (
                        proc := plot_info[0] if plot_info else get_plot_method(plot)
                    ) is None:
                        raise ValueError(
                            f"No plotting function specified or inferred from plot key: {plot}"
                        )
                    # drop post processors from kwargs
                    proc_kwargs = {
                        k: v for k, v in kwargs.items() if k not in TABLE_POSTPROCESSORS
                    }
                    table_data = METHOD[proc](df, **proc_kwargs)
                    for post_processor in TABLE_POSTPROCESSORS & set(kwargs):
                        table_data = METHOD[post_processor](
                            table_data, kwargs[post_processor]
                        )
                    var[plot_key] = table_data.to_html(index=False)
                case "figure":
                    if (
                        proc := plot_info[0] if plot_info else get_plot_method(plot)
                    ) is None:
                        raise ValueError(
                            f"No plotting function specified or inferred from plot key: {plot}"
                        )
                    var.update(render_figure(METHOD[proc](df, **kwargs), plot_key))

        report_data = chevron.render(template_text, var)
        Path(output_file).write_text(report_data)
        msg_ok("report", "wrote " + output_file)

        if output_bucket:
            store_s3(
                report_data,
                [f"{self.name}/index.html", f"{self.name}/{date}.html"],
                bucket_name=output_bucket,
                content_type="text/html",
            )
        if cloudfront_distribution:
            invalidate_cache(cloudfront_distribution)
