"""
Library of plots used in most outbreaks
"""

import logging

import pandas as pd
import numpy as np
from dateutil.parser import ParserError
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .util import (
    percentage_occurrence,
    name_bin,
    AGE_BINS,
    get_age_bins,
    non_null_unique,
)
from .theme import (
    FONT,
    TITLE_FONT,
    PALETTE,
    LEGEND_FONT_SIZE,
    BLUE_PRIMARY_COLOR,
    PRIMARY_COLOR,
    SECONDARY_COLOR,
    BG_COLOR,
    FG_COLOR,
    GRID_COLOR,
)

REGEX_DATE = r"^202\d-[0,1]\d-[0-3]\d"

pd.options.mode.chained_assignment = None


def get_countries_with_status(
    df: pd.DataFrame,
    country_col: str,
    statuses: list[str],
    status_col: str = "Case_status",
) -> dict[str, int]:
    """For a set of statuses, gets number of countries which have the status,
    and the number of countries who have that status exclusively"""

    out = {}
    for status in statuses:
        out[f"n_countries_{status}"] = len(
            df[df[status_col] == status][country_col].unique()
        )
        out[f"n_countries_{status}_only"] = len(
            set(df[df[status_col] == status][country_col])
            - set(df[df[status_col] != status][country_col])
        )
    return out


def get_countries_with_anyof_statuses(
    df: pd.DataFrame,
    country_col: str,
    statuses: list[str],
    status_col: str = "Case_status",
) -> dict[str, int]:
    "Gets number of countries which have any of the statuses listed"
    return {
        "n_countries_" + "_or_".join(sorted(statuses)): len(
            df[df[status_col].isin(statuses)][country_col].unique()
        )
    }


def get_age_bin_data(df: pd.DataFrame) -> pd.DataFrame:
    confirmed = df[df.Case_status == "confirmed"][["Age", "Gender"]]
    confirmed["Gender"] = confirmed.Gender.apply(
        lambda x: x.strip() if isinstance(x, str) else x
    )
    age_gender = (
        confirmed.groupby(["Age", "Gender"])
        .size()
        .reset_index()
        .rename(columns={0: "n"})
    )
    age_gender["Age_bins"] = age_gender.Age.map(get_age_bins)
    age_gender["distributed_n"] = age_gender.n / age_gender.Age_bins.map(len)

    data = []
    for row in age_gender.itertuples():
        for bin_idx in row.Age_bins:
            data.append((name_bin(bin_idx), row.Gender, row.distributed_n))
    final = pd.DataFrame(data, columns=["Bin", "Gender", "N"])
    return final.groupby(["Bin", "Gender"]).sum().reset_index()


def get_delays(
    df: pd.DataFrame, target_col: str, onset_col: str = "Date_onset"
) -> pd.Series:
    both = df[
        ~pd.isna(df[target_col])
        & ~pd.isna(df[onset_col])
        & df[target_col].astype(str).str.fullmatch(REGEX_DATE)
        & df[onset_col].astype(str).str.fullmatch(REGEX_DATE)
    ]
    try:
        both[target_col] = pd.to_datetime(both[target_col])
        both[onset_col] = pd.to_datetime(both[onset_col])
    except ParserError:
        logging.error("Error occured when parsing date from column")
        raise
    return both[target_col] - both[onset_col]


def get_epicurve(
    df: pd.DataFrame,
    date_col: str,
    groupby_col: str,
    values: list[str] | None = None,
    cumulative: bool = True,
) -> pd.DataFrame:
    """Returns epidemic curve

    Parameters
    ----------
    df
        Data from which epicurve is obtained
    date_col
        Date column to use
    groupby_col
        Column to group by, e.g. Case_status
    values
        Values of the column to plot, e.g. ['confirmed', 'probable']
    cumulative
        Whether to return cumulative counts (default = true)
    """
    values = non_null_unique(df[groupby_col]) if values is None else values
    epicurve = (
        df[~pd.isna(df[date_col]) & df[groupby_col].isin(values)]
        .groupby([date_col, groupby_col])
        .size()
        .reset_index()
        .pivot(index=date_col, columns=groupby_col, values=0)
        .fillna(0)
        .astype(int)
    )
    return epicurve.cumsum() if cumulative else epicurve


def get_counts(df: pd.DataFrame, date_col: str) -> dict[str, int]:
    status = df.Case_status.value_counts()
    confirmed = df[df.Case_status == "confirmed"]
    return {
        "n_confirmed": int(status.confirmed),
        "n_probable": int(status.get("probable", 0)),
        "n_suspected": int(status.get("suspected", 0)),
        "date": str(df[~pd.isna(df[date_col])][date_col].max().date()),
        "pc_valid_age_gender": percentage_occurrence(
            confirmed,
            (~confirmed.Age.isna()) & (~confirmed.Gender.isna()),
        ),
    }


def get_timeseries_location_status(
    df: pd.DataFrame, fill_index: bool = False
) -> pd.DataFrame:
    "Returns a time series case dataset (number of cases by location by date stratified by confirmed and probable)"
    statuses = ["confirmed", "probable"]
    df = df[
        df.Case_status.isin(statuses)
        & ~pd.isna(df.Date_onset_estimated)
        & ~pd.isna(df.Location_District)
    ]
    locations = sorted(set(df.Location_District)) + [None]
    mindate, maxdate = df.Date_onset_estimated.min(), df.Date_onset_estimated.max()

    def timeseries_for_location(location: str | None) -> pd.DataFrame:
        if location is None:
            counts = (
                df.groupby(["Date_onset_estimated", "Case_status"])
                .size()
                .reset_index()
                .pivot(index="Date_onset_estimated", columns="Case_status", values=0)
                .fillna(0)
                .astype(int)
            )
        else:
            counts = (
                df[df.Location_District == location]
                .groupby(["Date_onset_estimated", "Case_status"])
                .size()
                .reset_index()
                .pivot(index="Date_onset_estimated", columns="Case_status", values=0)
                .fillna(0)
                .astype(int)
            )
        if fill_index:
            counts = counts.reindex(pd.date_range(mindate, maxdate), fill_value=0)
        for status in set(statuses) - set(counts.columns):
            counts[status] = 0
        counts = counts.rename(columns={s: "daily_" + s for s in statuses})
        for s in statuses:
            counts["cumulative_" + s] = counts["daily_" + s].cumsum()
        counts["Location_District"] = location if location else "Total"
        return counts

    timeseries = pd.concat(map(timeseries_for_location, locations)).fillna(0)
    for col in ["daily_" + s for s in statuses] + ["cumulative_" + s for s in statuses]:
        timeseries[col] = timeseries[col].astype(int)
    return timeseries.reset_index(names="Date_onset_estimated")


def plot_timeseries_location_status(
    df: pd.DataFrame, admin_column: str, columns: int = 3
):
    df = get_timeseries_location_status(df, fill_index=True)
    locations = sorted(set(df[admin_column]) - {"Total"})

    fig = make_subplots(
        rows=2, cols=3, subplot_titles=locations, shared_yaxes=True, shared_xaxes=True
    )

    for i, location in enumerate(locations):
        location_data = df[df[admin_column] == location]
        cur_row, cur_col = i // columns + 1, i % columns + 1
        fig.add_trace(
            go.Scatter(
                x=location_data.Date_onset_estimated,
                y=location_data.cumulative_confirmed,
                name="confirmed",
                line_color=PRIMARY_COLOR,
                line_width=3,
                showlegend=not bool(i),
            ),
            row=cur_row,
            col=cur_col,
        )
        fig.add_trace(
            go.Scatter(
                x=location_data.Date_onset_estimated,
                y=location_data.cumulative_probable,
                name="probable",
                line_color=SECONDARY_COLOR,
                line_width=3,
                showlegend=not bool(i),
            ),
            row=cur_row,
            col=cur_col,
        )
    fig.update_yaxes(
        range=[
            0,
            max(
                df[df.Location_District != "Total"].cumulative_confirmed.max(),
                df[df.Location_District != "Total"].cumulative_probable.max(),
            )
            + 1,
        ],
        gridcolor=GRID_COLOR,
        zerolinecolor="#d0d0d0",
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
    )
    fig.update_layout(
        plot_bgcolor=BG_COLOR,
        font_family=FONT,
        paper_bgcolor=BG_COLOR,
        hoverlabel_font_family=FONT,
        legend_font_family=TITLE_FONT,
        legend_font_size=LEGEND_FONT_SIZE,
    )
    for annotation in fig["layout"]["annotations"]:
        annotation["font"] = {
            "family": TITLE_FONT,
            "size": LEGEND_FONT_SIZE + 3,
            "color": FG_COLOR,
        }

    return fig


def plot_epicurve(
    df: pd.DataFrame,
    title: str,
    date_col: str,
    groupby_col: str,
    values: list[str] | None = None,
    cumulative: bool = True,
    palette: list[str] = PALETTE,
):
    values = non_null_unique(df[groupby_col]) if values is None else values
    data = get_epicurve(df, date_col, groupby_col, values, cumulative=cumulative)
    fig = go.Figure()
    for idx, value in enumerate(values):
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[value],
                name=value,
                line_color=palette[idx],
                line_width=3,
            ),
        )

    fig.update_xaxes(
        title_text=title,
        title_font_family=TITLE_FONT,
        title_font_color=FG_COLOR,
        gridcolor=GRID_COLOR,
    )

    fig.update_yaxes(
        title_text="Cumulative cases" if cumulative else "Cases",
        title_font_family=TITLE_FONT,
        title_font_color=FG_COLOR,
        gridcolor=GRID_COLOR,
        zeroline=False,
    )
    fig.update_layout(
        plot_bgcolor=BG_COLOR,
        font_family=FONT,
        paper_bgcolor=BG_COLOR,
        hoverlabel_font_family=FONT,
        legend_font_family=TITLE_FONT,
        legend_font_size=LEGEND_FONT_SIZE,
    )

    return fig


def plot_delay_distribution(
    df: pd.DataFrame,
    col: str,
    title: str,
    index: str,
    max_delay_days: int = 30,
):
    delays = get_delays(df, col).dt.days.value_counts()
    if max_delay_days not in delays:
        delays[max_delay_days] = 0
    delays = delays.reset_index().rename({"index": title, 0: "count"}, axis=1)
    fig = px.bar(
        delays,
        x=title,
        y="count",
        color_discrete_sequence=[PRIMARY_COLOR],
    )
    fig.update_layout(
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font_family=FONT,
        title=index,
        title_font_color=FG_COLOR,
        title_font_family=TITLE_FONT,
        hoverlabel_font_family=FONT,
        bargap=0.2,
    )
    fig.update_xaxes(
        title_font_family=TITLE_FONT,
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        title_font_color=FG_COLOR,
        linewidth=3,
    )
    fig.update_yaxes(
        title_font_family=TITLE_FONT,
        title_font_color=FG_COLOR,
        gridcolor=GRID_COLOR,
        showline=False,
    )

    return fig


def plot_age_gender(df: pd.DataFrame):
    df = get_age_bin_data(df)
    fig = go.Figure()
    vals = {}
    for row in df.itertuples():
        vals[(row.Bin, row.Gender)] = row.N

    bin_names = [name_bin(bin_idx) for bin_idx in range(len(AGE_BINS))]
    female_binvals = -np.array([vals.get((bin, "female"), 0) for bin in bin_names])
    male_binvals = np.array([vals.get((bin, "male"), 0) for bin in bin_names])

    y = bin_names
    max_binval = max(-female_binvals.max(), male_binvals.max())
    nearest = int(((max_binval // 5) + 1) * 5)
    ticks = np.linspace(-nearest, nearest, 2 * nearest + 1).astype(int)

    fig.update_yaxes(title="Age", title_font_family=TITLE_FONT, gridcolor=GRID_COLOR)
    fig.update_xaxes(
        range=[-nearest, nearest],
        tickvals=ticks,
        ticktext=list(map(abs, ticks)),
        title="Counts",
        title_font_family=TITLE_FONT,
        gridcolor=GRID_COLOR,
        title_font_color=FG_COLOR,
        zeroline=False,
    )
    fig.update_layout(
        {
            "barmode": "overlay",
            "bargap": 0.1,
            "template": "plotly_white",
            "font_family": FONT,
            "hoverlabel_font_family": FONT,
            "plot_bgcolor": BG_COLOR,
            "paper_bgcolor": BG_COLOR,
            "legend_font_family": TITLE_FONT,
            "legend_font_size": LEGEND_FONT_SIZE,
        }
    )

    fig.add_trace(
        go.Bar(
            y=y,
            x=male_binvals,
            orientation="h",
            name="male",
            hoverinfo="skip",
            hovertemplate=None,
            textposition="none",
            marker={"color": SECONDARY_COLOR},
        )
    )
    fig.add_trace(
        go.Bar(
            y=y,
            x=female_binvals,
            orientation="h",
            name="female",
            text=-female_binvals.astype("int"),
            hoverinfo="skip",
            hovertemplate=None,
            textposition="none",
            marker={"color": BLUE_PRIMARY_COLOR},
        )
    )

    return fig
