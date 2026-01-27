"""
Library of plots used in most outbreaks
"""
import collections
import logging
from typing import Any

import pandas as pd
import numpy as np
from dateutil.parser import ParserError
import plotly.graph_objects as go
import plotly.express as px

from plotly.subplots import make_subplots
from wordcloud import WordCloud
from datetime import timedelta

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
    LEGEND_BG_COLOR,
)

REGEX_DATE = r"^202\d-[0,1]\d-[0-3]\d"

pd.options.mode.chained_assignment = None

standard_plot_layout = {
    'plot_bgcolor': BG_COLOR,
    'font_family': FONT,
    'legend_font_family': TITLE_FONT,
    'legend_font_size': LEGEND_FONT_SIZE,
    'paper_bgcolor': BG_COLOR,
    'hoverlabel_font_family': FONT,
    'legend_bgcolor': LEGEND_BG_COLOR,
    'title_font_color': FG_COLOR,
    'title_font_family': TITLE_FONT,
}

standard_axis_layout = {
    'title_font_family': TITLE_FONT,
    'gridcolor': GRID_COLOR,
    'linecolor': GRID_COLOR,
    'title_font_color': FG_COLOR
}


def get_aggregate(
        df: pd.DataFrame, country_col: str, columns=list[tuple[str, str]]
) -> pd.DataFrame:
    "Get aggregate for line list"
    dfs = []
    for col, value in columns:
        dfs.append(df[df[col] == value].groupby(country_col).size().rename(value))
    return pd.DataFrame(dfs).T.fillna(0).astype(int).reset_index()


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


def get_counts(df: pd.DataFrame, date_col: str, static_counts: dict[str, int] = {}) -> dict[str, int]:
    status = df.Case_status.value_counts()
    confirmed = df[df.Case_status == "confirmed"]
    outcome = df['Outcome']
    counts = {
        "n_confirmed": int(status.confirmed),
        "n_probable": int(status.get("probable", 0)),
        "n_suspected": int(status.get("suspected", 0)),
        "n_dead": int(outcome.value_counts().get("death", 0)),
        "date": df[~pd.isna(df[date_col])][date_col].max().strftime('%Y-%m-%d'),
        "pc_valid_age_gender": percentage_occurrence(
            confirmed,
            (~confirmed.Age.isna()) & (~confirmed.Gender.isna()),
        ),
        **static_counts,
    }
    if 'Location_Admin1' in df.columns:
        location_admin1 = df['Location_Admin1']
        counts["n_unique_states"] = len(location_admin1.value_counts()),
    if 'Occupation' in df.columns:
        occupation = df[df.Case_status == "confirmed"]['Occupation'].dropna()
        counts["n_farm_workers_infected"] = sum('farm worker' in ov.lower() for ov in occupation.values)
    return counts


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


def get_trailing_case_count(df: pd.DataFrame, date_col: str, trailing_time_in_days: int):
    """Returns trailing case count

    Parameters
    ----------
    df
        Data from which trailing case count is obtained
    date_col
        Date column to use
    trailing_time_in_days
        How many days cases will trail on chart
    """
    date_and_count = df[date_col].value_counts().sort_index()
    x = date_and_count.index
    y = date_and_count.values

    # For each of the case occurrences propagate values for the next "trailing_time_in_days" days
    trailing_data = collections.defaultdict(int)
    for x_idx in range(len(x)):
        for i in range(trailing_time_in_days):
            date = x[x_idx] + timedelta(i)
            date = date.strftime("%Y-%m-%d")
            trailing_data[date] += int(y[x_idx])
    return trailing_data


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
        **standard_axis_layout,
        range=[
            0,
            max(
                df[df.Location_District != "Total"].cumulative_confirmed.max(),
                df[df.Location_District != "Total"].cumulative_probable.max(),
            )
            + 1,
        ],
        zerolinecolor="#d0d0d0",
    )
    fig.update_xaxes(**standard_axis_layout)
    fig.update_layout(**standard_plot_layout)
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
        if value in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data[value],
                    name=value,
                    line_color=palette[idx],  # turn off for higher counts of elements
                    line_width=3,
                ),
            )

    fig.update_xaxes(
        **standard_axis_layout,
        title_text=title,
    )

    fig.update_yaxes(
        **standard_axis_layout,
        title_text="Cumulative cases" if cumulative else "Cases",
        zeroline=False,
    )
    fig.update_layout(
        **standard_plot_layout,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
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
        **standard_plot_layout,
        title=index,
        bargap=0.2,
        margin={"l": 0, "r": 0, "t": 5, "b": 5},
    )
    fig.update_xaxes(
        **standard_axis_layout,
        linewidth=3,
    )
    fig.update_yaxes(
        **standard_axis_layout,
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

    fig.update_yaxes(**standard_axis_layout, title="Age")
    fig.update_xaxes(
        **standard_axis_layout,
        range=[-nearest, nearest],
        tickvals=ticks,
        ticktext=list(map(abs, ticks)),
        title="Counts",
        zeroline=False,
    )
    fig.update_layout(
        **standard_plot_layout,
        barmode="overlay",
        bargap=0.1,
        template="plotly_white",
        margin={"l": 0, "r": 0, "t": 5, "b": 5},
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


def plot_data_availability(df: pd.DataFrame):
    """Creates data availability plot horizontal barplot

    Parameters
    ----------
    df
        Data from which column availability is obtained
    """
    # Get metadata (column names, count, row count)
    y = df.columns.values
    row_count = len(df.index)
    column_count = len(y)

    fig = go.Figure()
    fig.update_yaxes(**standard_axis_layout, title="Variable", dtick=1)
    fig.update_xaxes(
        **standard_axis_layout,
        tickvals=np.linspace(0., row_count, num=10 + 1),
        ticktext=list(map(lambda t: f'{t / 10 * 100}%', range(11))),
        title="Percentage of available data",
        zeroline=False,
    )
    fig.update_layout(
        **standard_plot_layout,
        barmode="overlay",
        bargap=0.1,
        template="plotly_white",
        height=250 + column_count * 15,  # Scale the height depending on how many columns are in the dataframe
        margin={"l": 0, "r": 0, "t": 5, "b": 5},
    )

    fig.add_trace(
        go.Bar(
            y=y,
            x=df.count(),
            orientation="h",
            name="",
            hovertemplate=None,
            textposition="none",
            marker={"color": PRIMARY_COLOR},
        )
    )
    fig.update_traces(
        customdata=list(map(lambda c: round(c / row_count * 100, 1), df.count())),  # Completeness percentage
        hovertemplate="<br>".join([
            "%{y} completeness: %{customdata}%",
        ])
    )

    return fig


# TODO Ideally we would want the term frequency plot to generate automatically from the dataset
#      due to complex preprocessing for Avian Influenza 2024 we need to extract it manually
def plot_term_frequency(_: pd.DataFrame, term_column: str, term_values: dict[str, int], total_entry_count: int,
                        y_label: str):
    """Creates term frequency horizontal barplot

    Parameters
    ----------
    term_column
        Name of term column containing terms
    term_values
        Terms and their cardinality for wordcloud visualization
    total_entry_count
        Number of all entries that are used to calculate word frequency
    y_label
        Y axis label
    """
    y = list(term_values.keys())
    term_occurrences = pd.Series(data=term_values, index=y)

    fig = go.Figure()
    fig.update_yaxes(**standard_axis_layout, title=y_label, dtick=1)
    fig.update_xaxes(
        **standard_axis_layout,
        tickvals=np.linspace(0., total_entry_count, num=10 + 1),
        ticktext=list(map(lambda t: f'{t / 10 * 100}%', range(11))),
        title=f"Term frequency in {term_column}",
        zeroline=False,
    )

    fig.update_layout(
        **standard_plot_layout,
        barmode="overlay",
        bargap=0.1,
        template="plotly_white",
        height=250 + len(y) * 15,
        margin={"l": 0, "r": 0, "t": 5, "b": 5},
    )

    fig.add_trace(
        go.Bar(
            y=y,
            x=pd.Series(data=term_values, index=y),
            orientation="h",
            name="",
            hovertemplate=None,
            textposition="none",
            marker={"color": PRIMARY_COLOR},
        )
    )

    # Update to show percentage on hover
    fig.update_traces(
        customdata=list(map(lambda c: round(c / total_entry_count * 100, 1), term_occurrences)),
        hovertemplate="<br>".join([
            "%{y} : %{customdata}%",
        ])
    )

    return fig


# TODO Ideally we would want the wordcloud to generate automatically from the dataset
#      due to complex preprocessing for Avian Influenza 2024 we need to extract it manually
def plot_wordcloud(_: pd.DataFrame, term_values: dict[str, float]):
    """Creates wordcloud visualization

    Parameters
    ----------
    term_values
        Terms and their cardinality for wordcloud visualization
    """
    # Constants
    img_width = 1600
    img_height = 800
    # we use scaling to generate higher resolution image and make it fit in smaller container
    # while maintaining resolution
    scale_factor = 0.5

    wordcloud = WordCloud(
        background_color="rgba(255, 255, 255, 0)",
        mode="RGBA",
        width=img_width,
        height=img_height,
        prefer_horizontal=1
    ).generate_from_frequencies(term_values)

    fig = go.Figure()

    # Add invisible scatter trace.
    # This trace is added to help the autoresize logic work.
    fig.add_trace(
        go.Scatter(
            x=[0, img_width * scale_factor],
            y=[0, img_height * scale_factor],
            mode="markers",
            marker_opacity=0
        )
    )

    # Configure axes
    fig.update_xaxes(
        visible=False,
        range=[0, img_width * scale_factor]
    )
    fig.update_yaxes(
        visible=False,
        range=[0, img_height * scale_factor],
        scaleanchor="x"
    )

    # Add image to plotly canvas
    fig.add_layout_image(
        dict(
            x=0,
            sizex=img_width * scale_factor,
            y=img_height * scale_factor,
            sizey=img_height * scale_factor,
            xref="x",
            yref="y",
            opacity=1.0,
            layer="below",
            sizing="stretch",
            source=wordcloud.to_image())
    )

    fig.update_layout(
        **standard_plot_layout,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )

    return fig


def plot_trailing_case_count(df: pd.DataFrame, date_col: str, trailing_time_in_days: int, x_label: str, y_label: str,
                             palette: list[str] = PALETTE):
    """Creates trailing case count plot

    Parameters
    ----------
    df
        Data from which trailing case count is obtained
    date_col
        Date column to use
    trailing_time_in_days
        How many days cases will trail on chart
    x_label
        X axis label
    y_label
        Y axis label
    palette
        Color palette for plot
    """
    trailing_data = get_trailing_case_count(df, date_col, trailing_time_in_days)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=list(trailing_data.keys()), y=list(trailing_data.values()), line_color=palette[0], line_width=3))
    fig.update_yaxes(**standard_axis_layout, title=x_label)
    fig.update_xaxes(**standard_axis_layout, title=y_label)
    fig.update_layout(
        **standard_plot_layout,
        barmode="overlay",
        bargap=0.1,
        template="plotly_white",
        margin={"l": 0, "r": 0, "t": 5, "b": 5},
    )
    return fig


def stacked_barchart(df: pd.DataFrame, y_axis: Any, color_column: str, x_label: str, y_label: str,
                     palette: list[str] = PALETTE):
    """Creates stacked bar chart plot

    Parameters
    ----------
    df
        Data from which epicurve is obtained
    y_axis
        Values for Y axis
    color_column
        Column name used in the plot for bar color
    x_label
        X axis label
    y_label
        Y axis label
    palette
        Color palette for plot
    """
    fig = px.bar(df, y=y_axis, color=color_column, orientation='h', color_discrete_sequence=palette)
    fig.update_layout(
        template="plotly_white",
        **standard_plot_layout,
        margin={"l": 0, "r": 0, "t": 5, "b": 5},
    )
    fig.update_xaxes(title=x_label)
    fig.update_yaxes(title=y_label)
    fig.update_traces(hoverinfo="skip", hovertemplate=None)
    return fig
