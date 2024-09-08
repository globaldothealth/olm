"""
Briefing report generator module
"""

import datetime
from typing import Callable, Any
from pathlib import Path

import chevron
import plotly.io
import plotly.graph_objects as go

from .util import read_csv, store_s3, invalidate_cache

PlotFunction = Callable[..., dict[str, Any] | go.Figure]
PlotData = tuple[str, PlotFunction, dict[str, Any]]


def render(template: Path, variables: dict[str, Any]) -> str:
    with template.open() as f:
        return chevron.render(f, variables)


def render_figure(fig, key: str) -> str:
    return {key: plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)}


def make_report(
    outbreak_name: str,
    data_url: str,
    plots: list[PlotData],
    date_columns: list[str] = [],
    output_bucket: str | None = None,
    cloudfront_distribution: str | None = None,
):
    """Build epidemiological report

    Parameters
    ----------
    outbreak_name
        Name of the outbreak
    data_url
        Data file for the outbreak, can be a S3 URL
    plots
        List of plot or table specifications for the outbreak, such as those
        in :module:`olm.outbreaks`
    date_columns
        If specified, lists additional date columns to be passed to read_csv()
    output_bucket
        Output S3 bucket to write result to, in addition to local HTML output
        to {outbreak_name}.html
    cloudfront_distribution
        If specified, invalidates the cache for the cloudfront distribution
        without which changes are not made available
    """
    assert " " not in outbreak_name, "Outbreak name should not have spaces"
    date = datetime.datetime.today().date()
    output_file = f"{outbreak_name}.html"
    if not (template := Path(__file__).parent / "outbreaks" / output_file).exists():
        raise FileNotFoundError(f"Template for outbreak not found at: {template}")
    var = {"published_date": str(date)}
    df = read_csv(data_url, date_columns)
    for plot in plots:
        kwargs = {} if len(plot) == 2 else plot[2]
        plot_type = plot[0].split("/")[0]
        match plot_type:
            case "data":
                var.update(plot[1](df, **kwargs))
            case "table":
                var[plot[0].removeprefix("table/")] = plot[1](df, **kwargs).to_html(
                    index=False
                )
            case "figure":
                var.update(
                    render_figure(
                        plot[1](df, **kwargs), plot[0].removeprefix("figure/")
                    )
                )

    report_data = render(template, var)
    Path(output_file).write_text(report_data)
    print("wrote", output_file)

    if output_bucket:
        store_s3(
            report_data,
            [f"{outbreak_name}/index.html", f"{outbreak_name}/{date}.html"],
            bucket_name=output_bucket,
            content_type="text/html",
        )
    if cloudfront_distribution:
        invalidate_cache(cloudfront_distribution)
