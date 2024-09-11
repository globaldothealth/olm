"""
Briefing report generator module
"""

import datetime
from pathlib import Path

import chevron
import plotly.io

from .types import OutbreakInfo
from .util import read_csv, store_s3, invalidate_cache, msg_ok

TEMPLATES = Path(__file__).parent / "outbreaks"
HEADER = (TEMPLATES / "_header.html").read_text()
FOOTER = (TEMPLATES / "_footer.html").read_text()


def render_figure(fig, key: str) -> str:
    return {key: plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)}


def make_report(
    outbreak_name: str,
    data_url: str,
    outbreak_info: OutbreakInfo,
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
    outbreak_info
        Information about the outbreak, described in :module:`olm.outbreaks`
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
    if not (template := TEMPLATES / output_file).exists():
        raise FileNotFoundError(f"Template for outbreak not found at: {template}")
    template_text = HEADER + template.read_text() + FOOTER
    var = {
        "description": outbreak_info["description"],
        "id": outbreak_info["id"],
        "published_date": str(date),
        "data_url": outbreak_info.get("url", ""),
    }
    df = read_csv(data_url, outbreak_info.get("additional_date_columns", []))
    for plot in outbreak_info["plots"]:
        kwargs = {} if len(plot) == 2 else plot[2]
        plot_type = plot[0].split("/")[0]
        match plot_type:
            case "data":
                var.update(plot[1](df, **kwargs))
            case "table":
                table_data = plot[1](df, **kwargs)
                for post_processor in plot[3:]:
                    table_data = post_processor(table_data)
                var[plot[0].removeprefix("table/")] = table_data.to_html(index=False)
            case "figure":
                var.update(
                    render_figure(
                        plot[1](df, **kwargs), plot[0].removeprefix("figure/")
                    )
                )

    report_data = chevron.render(template_text, var)
    Path(output_file).write_text(report_data)
    msg_ok("report", "wrote " + output_file)

    if output_bucket:
        store_s3(
            report_data,
            [f"{outbreak_name}/index.html", f"{outbreak_name}/{date}.html"],
            bucket_name=output_bucket,
            content_type="text/html",
        )
    if cloudfront_distribution:
        invalidate_cache(cloudfront_distribution)
