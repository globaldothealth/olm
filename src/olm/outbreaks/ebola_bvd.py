"Ebola BVD outbreak specific functions"

import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..plots import standard_plot_layout, standard_axis_layout, PALETTE

def html_ebola_bvd_country_counts(df: pd.DataFrame, last_report_date: str, drc_new_cases: int, drc_new_deaths: int):
    """Generate HTML table of confirmed cases and deaths by country"""
    countries = df['Location_Admin0'].unique()
    last_report_ts = pd.to_datetime(last_report_date, errors='coerce')

    row_data = []
    for country in countries:
        country_df = df[df['Location_Admin0'] == country]
        confirmed = country_df[country_df['Case_status'] == 'confirmed']
        # Deaths include 'a ventiler' (confirmed, pending assignment) records
        confirmed_for_deaths = country_df[country_df['Case_status'].isin(['confirmed', 'a ventiler'])]

        # Calculate confirmed cases counts
        date_confirmation = pd.to_datetime(confirmed['Date_confirmation'], errors='coerce')
        new_confirmed_count = int((date_confirmation > last_report_ts).sum())

        confirmed_count = len(confirmed)

        # Calculate confirmed deaths counts (same population for total and new)
        deaths = confirmed_for_deaths[confirmed_for_deaths['Outcome'] == 'Death']
        confirmed_deaths_count = len(deaths)
        date_death = pd.to_datetime(deaths['Date_death'], errors='coerce')
        new_confirmed_deaths_count = int((date_death > last_report_ts).sum())

        # Use variable numbers for DRC
        if country == "Democratic Republic of the Congo":
            new_confirmed_count = drc_new_cases
            new_confirmed_deaths_count = drc_new_deaths

        row_data.append({
            'country': country,
            'confirmed_count': confirmed_count,
            'new_confirmed_count': new_confirmed_count,
            'confirmed_deaths_count': confirmed_deaths_count,
            'new_confirmed_deaths_count': new_confirmed_deaths_count,
            # CFR denominator uses the same population as the deaths numerator
            'cfr_denominator': len(confirmed_for_deaths),
        })

    sorted_row_data = sorted(
        row_data,
        key=lambda x: (
            -(x.get('new_confirmed_count') or 0),
            -(x.get('new_confirmed_deaths_count') or 0),
            -(x.get('confirmed_count') or 0),
        )
    )

    def fmt_total(n: int) -> str:
        return f"{n:,}"

    def fmt_new(n: int) -> str:
        return f" +{n:,}" if n > 0 else "&mdash;"

    def render_row(r: dict, row_class: str = "") -> str:
        cases_state = "is-up" if r['new_confirmed_count'] > 0 else "is-flat"
        deaths_state = "is-up" if r['new_confirmed_deaths_count'] > 0 else "is-flat"
        tr_class = f' class="{row_class}"' if row_class else ""
        return (
            f'<tr{tr_class}>'
            f'<td class="country">{html.escape(str(r["country"]))}</td>'
            f'<td class="num new {cases_state}">{fmt_new(r["new_confirmed_count"])}</td>'
            f'<td class="num {cases_state}">{fmt_total(r["confirmed_count"])}</td>'
            f'<td class="num new {deaths_state}">{fmt_new(r["new_confirmed_deaths_count"])}</td>'
            f'<td class="num {deaths_state}">{fmt_total(r["confirmed_deaths_count"])}</td>'
            '</tr>'
        )

    rows = [render_row(r) for r in sorted_row_data]

    totals = {
        key: sum(r[key] for r in row_data)
        for key in ('confirmed_count', 'new_confirmed_count', 'confirmed_deaths_count',
                    'new_confirmed_deaths_count', 'cfr_denominator')
    }
    totals['country'] = 'All countries'
    total_row = render_row(totals, row_class="total-row")

    thead = (
        '<thead>'
        '<tr>'
        '<th rowspan="2">Country</th>'
        '<th colspan="2">Confirmed cases</th>'
        '<th colspan="2">Confirmed deaths</th>'
        '</tr>'
        '<tr>'
        f'<th class="sub">New</th><th class="sub">Total</th>'
        f'<th class="sub">New</th><th class="sub">Total</th>'
        '</tr>'
        '</thead>'
    )
    tfoot = f'<tfoot>{total_row}</tfoot>'
    return (
        '<table class="summary-table country-counts-table">'
        + thead + '<tbody>' + ''.join(rows) + '</tbody>' + tfoot
        + '</table>'
    )



def plot_ebola_bvd_health_zone_barchart(df: pd.DataFrame):
    """
    Creates stacked bar chart of Ebola BVD cases by health zone and outcome, with health zones grouped by Location Admin1.
    """
    df = df.copy()
    df = df[df["Location_Admin0"] == "Democratic Republic of the Congo"]
    df = df[(df["Case_status"] == 'confirmed') | (df["Case_status"] == 'a ventiler')]
    y_values = df['Health zone']
    y_empty_mask = y_values.isna() | (y_values.astype(str).str.strip() == "")
    df.loc[y_empty_mask, 'Health zone'] = "a ventiler"

    color_values = df['Outcome']
    replace_mask = (
            color_values.isna()
            | (color_values.astype(str).str.strip() == "")
            | (color_values.astype(str).str.strip().str.lower() == "recovered")
    )
    df.loc[replace_mask, 'Outcome'] = "Confirmed case"
    replace_mask2 = (color_values.astype(str).str.strip().str.lower() == "death")
    df.loc[replace_mask2, 'Outcome'] = "Confirmed death"

    death_as_case = df[df['Outcome'] == "Confirmed death"].copy()
    death_as_case['Outcome'] = "Confirmed case"
    df = pd.concat([df, death_as_case], ignore_index=True)

    df = df.groupby(['Health zone', 'Location Admin1', 'Outcome']).size().reset_index(name='count')
    combined_axis = f"Health zone (Location Admin 1)"
    df[combined_axis] = df.apply(
        lambda row: f"{row['Health zone']} ({row['Location Admin1']})", axis=1
    )

    new_color_column = "Case status"
    df = df.rename(columns={'Outcome': new_color_column})

    order = (
        df[df[new_color_column] == "Confirmed case"]
        .sort_values("count", ascending=False)[combined_axis]
        .tolist()
    )
    tick_text_map = {
        row[combined_axis]: (
            f"<b><i>{row['Health zone']}</i></b> ({row['Location Admin1']})"
            if str(row['Health zone']).strip().lower() == "a ventiler"
            else f"<b>{row['Health zone']}</b> ({row['Location Admin1']})"
        )
        for _, row in df[[combined_axis, 'Health zone', 'Location Admin1']].drop_duplicates().iterrows()
    }

    fig = px.bar(
        df,
        y='count',
        x=combined_axis,
        color=new_color_column,
        orientation='v',
        color_discrete_sequence=PALETTE,
        category_orders={combined_axis: order},
        log_x=False,
    )
    fig.update_layout(
        barmode="overlay",
        template="plotly_white",
        **standard_plot_layout,
        width=800,
        margin={"l": 0, "r": 0, "t": 5, "b": 120},
        legend={"x": 0.9, "y": 0.9, "xanchor": "right"},
    )
    fig.update_xaxes(
        title='Health zone',
        tickmode='array',
        tickvals=order,
        ticktext=[tick_text_map.get(label, label) for label in order],
    )
    fig.update_yaxes(title='Case count')
    return fig


# Administrative levels of the DRC that the area charts can be drawn for, and the linelist column of each
ADMIN_COLUMNS = {1: "Location Admin1", 2: "Health zone"}


def _area_moving_averages(df: pd.DataFrame, window: int, admin_level: int, date_limit: str | None):
    """Moving average of daily confirmed DRC cases per area, over the whole outbreak span.

    Areas are provinces (`admin_level` 1, column "Location Admin1") or health zones (`admin_level` 2, column
    "Health zone"); cases without a value for the level are left out.

    The average at a date covers that day and the `window` - 1 days before it (fewer at the very start).

    Returns ``(totals, x, y, daily)``: confirmed case totals per area (highest first), the dates as
    ``YYYY-MM-DD`` strings, and dicts mapping each area to its moving average (rounded to 1 decimal) and to its
    daily case counts, one value per date.
    """
    if admin_level not in ADMIN_COLUMNS:
        raise ValueError(f"admin_level must be one of {sorted(ADMIN_COLUMNS)}, got: {admin_level!r}")
    column = ADMIN_COLUMNS[admin_level]
    df = df[
        (df["Location_Admin0"] == "Democratic Republic of the Congo")
        & (df["Case_status"] == "confirmed")
        & df["Date_confirmation"].notna()
    ]
    totals = df[column].value_counts()  # sorted, highest first
    end = pd.to_datetime(date_limit) if date_limit is not None else df["Date_confirmation"].max()
    full_range = pd.date_range(df["Date_confirmation"].min(), end)
    x = [d.strftime("%Y-%m-%d") for d in full_range]
    daily = {
        area: df.loc[df[column] == area, "Date_confirmation"].value_counts().reindex(full_range, fill_value=0)
        for area in totals.index
    }
    y = {area: counts.rolling(window, min_periods=1).mean().round(1).tolist() for area, counts in daily.items()}
    return totals, x, y, {area: counts.tolist() for area, counts in daily.items()}


def _zone_dropdown(slot: int, totals: pd.Series, dates: list[str], counts: dict[str, list[int]],
                   daily: dict[str, list[int]] | None = None, daily_slot: int | None = None, **position) -> dict:
    """Plotly dropdown (``updatemenus`` entry) which swaps the data of trace `slot` for the chosen area (province or health zone).

    Options are "None" (hides the trace) followed by every area with its total confirmed cases. The border has the
    colour of the trace (``PALETTE[slot]``). If `daily` and `daily_slot` are given, the trace `daily_slot` (e.g.
    a bar trace of daily counts) is swapped together with the main one. `position` is passed on to the menu
    (``x``, ``y``, ``active``, ...).
    """
    traces = [slot] + ([daily_slot] if daily is not None else [])
    buttons = [{"label": "None", "method": "restyle", "args": [{"visible": [False] * len(traces)}, traces]}] + [
        {"label": f"{zone} ({n:,})", "method": "restyle",
         "args": [{"x": [dates] * len(traces), "y": [counts[zone]] + ([daily[zone]] if daily else []),
                   "name": [zone, "Daily cases"][:len(traces)], "visible": [True] * len(traces)}, traces]}
        for zone, n in totals.items()
    ]
    return {"type": "dropdown", "direction": "down", "showactive": True, "xanchor": "left", "yanchor": "bottom",
            "bordercolor": PALETTE[slot], "borderwidth": 3, "bgcolor": "#fff", "buttons": buttons, **position}


def _area_cases(df: pd.DataFrame, window: int, admin_level: int, date_limit: str | None,
                           columns: int, max_areas: int | None, dropdowns: bool, scale_toggle: bool = False):
    """Grid of panels, one per area (see `_area_moving_averages`), ordered by confirmed cases (highest first,
    row by row). Each panel shows the daily case count as bars behind the moving average line, has its own date
    and y axis labels and titles, and all panels share one y scale and the full outbreak date range.

    Without `dropdowns` the panel title is the area name and its total confirmed cases, in all panels with the
    same colour. With `dropdowns` the first `max_areas` areas are shown and a native plotly dropdown above each
    panel (see `_zone_dropdown`), labelled "Health Zone:", swaps the area; the dropdown replaces the title. All
    panels use the same colour. Traces ``0..n-1`` are the lines and ``n..2n-1`` the bars of panels ``0..n-1``.

    With `scale_toggle` a "Plot scale:" label and two plotly buttons at the top right switch between "absolute"
    (all panels share the y scale, the default) and "relative" (each panel scales to its own data, so small areas
    stay readable) by setting or clearing ``matches`` on every y axis.
    """
    totals, x, y, daily = _area_moving_averages(df, window, admin_level, date_limit)
    areas = totals.index[:max_areas].tolist()
    n = len(areas)
    rows = -(-n // columns)  # ceil
    row_px = 300  # height of a panel including the date labels and title below it and the title/dropdown above
    fig = make_subplots(
        rows=rows, cols=columns, horizontal_spacing=0.12, vertical_spacing=min(120 / (row_px * rows), 0.5 / rows),
        subplot_titles=None if dropdowns else [f"{area} ({totals[area]:,})" for area in areas],
    )
    position = lambda i: {"row": i // columns + 1, "col": i % columns + 1}
    for i, area in enumerate(areas):
        fig.add_trace(go.Scatter(x=x, y=y[area], name=area if dropdowns else f"{window}-day average",
                                 line_color=PALETTE[0], line_width=2), **position(i))
    for i, area in enumerate(areas):  # bars; plotly always draws them below the lines
        fig.add_trace(go.Bar(x=x, y=daily[area], name="Daily cases", marker_color=PALETTE[0], opacity=0.35),
                      **position(i))
    fig.update_xaxes(**standard_axis_layout, range=[x[0], x[-1]], dtick="M1", tickformat="%b<br>%Y",
                     title_text="Date of confirmation")
    fig.update_yaxes(**standard_axis_layout, zeroline=False, matches="y", rangemode="tozero",
                     title_text=f"Daily cases and {window}-day average")
    menus = []
    if dropdowns:
        for i in range(n):
            axes = fig.get_subplot(**position(i))  # place each dropdown above its panel
            left, top_edge = axes.xaxis.domain[0], axes.yaxis.domain[1] + 0.01
            fig.add_annotation(text="Health Zone:", xref="paper", yref="paper", x=left, y=top_edge, xanchor="left",
                               yanchor="bottom", yshift=8, xshift=-10, showarrow=False, font={"size": 14})
            # no border, and shifted right by about the width of the label above (plotly sizes the box itself)
            menus.append(_zone_dropdown(i, totals, x, y, daily, i + n, x=left, y=top_edge, active=i + 1,
                                        borderwidth=0, pad={"l": 80}, font={"size": 14}))
    else:
        for annotation in fig["layout"]["annotations"]:  # panel titles
            annotation["font"] = {"size": 14}
    top = 50 + 40 * scale_toggle  # room for the dropdowns / panel titles, and the scale buttons above them
    if scale_toggle:
        axes = ["yaxis"] + [f"yaxis{k}" for k in range(2, n + 1)]
        buttons_y = 1 + (top - 10) / (row_px * rows + top)
        # the buttons are right aligned; their width is fixed by plotly (about 127px for these two labels), so the
        # label is placed that far (plus an 8px gap) to the left of the right edge. Plotly overshoots the right edge a bit, hence `pad`
        fig.add_annotation(text="Plot scale:", xref="paper", yref="paper", x=1, y=buttons_y, xanchor="right",
                           yanchor="top", yshift=-6, xshift=-145, showarrow=False, font={"size": 13})
        menus.append({
            "type": "buttons", "direction": "right", "showactive": True, "active": 0, "bgcolor": "#fff",
            "x": 1, "xanchor": "right", "y": buttons_y, "yanchor": "top", "pad": {"r": 4},
            "buttons": [
                {"label": "absolute", "method": "relayout",
                 "args": [{**{f"{a}.matches": "y" for a in axes}, **{f"{a}.autorange": True for a in axes}}]},
                {"label": "relative", "method": "relayout",
                 "args": [{**{f"{a}.matches": None for a in axes}, **{f"{a}.autorange": True for a in axes}}]},
            ],
        })
    fig.update_layout(**standard_plot_layout, showlegend=False, bargap=0.1, updatemenus=menus,
                      height=row_px * rows + top, margin={"l": 0, "r": 0, "t": top, "b": 0})
    return fig


def plot_province_cases(df: pd.DataFrame, window: int = 7, date_limit: str | None = None,
                                   columns: int = 2, max_areas: int | None = None):
    """Panel per DRC province (all of them by default), 2 per row, titled with the province and its total of
    confirmed cases: daily confirmed cases as bars and their `window`-day moving average as a line, see
    `_area_cases`. Buttons at the top right ("Plot scale") switch between one shared, absolute y scale (default) and a
    relative one, i.e. a y scale per province, as small provinces are unreadable on the shared one.

    Parameters
    ----------
    df
        Linelist; only confirmed DRC cases with a confirmation date are used
    window
        Moving average window in days
    date_limit
        Last date shown on the charts, defaults to the latest confirmation date
    columns
        Number of panels per row
    max_areas
        Only show this many provinces, those with the most confirmed cases (default: all)
    """
    return _area_cases(df, window, 1, date_limit, columns, max_areas, dropdowns=False, scale_toggle=True)


def plot_health_zone_cases(df: pd.DataFrame, window: int = 7, date_limit: str | None = None,
                                      slots: int = 4, columns: int = 2):
    """Panels for `slots` DRC health zones at a time (2x2 by default), each with its own native plotly dropdown
    above it to choose the health zone from all of them (or "None" to hide it). Uses only plotly ``updatemenus``,
    so no custom HTML or JS is needed. Panels start with the health zones with the most confirmed cases, see
    `_area_cases`.

    Plotly dropdowns are stateless, so a health zone picked in one panel is still offered in the others.
    Picking it twice shows it in both panels.

    Parameters
    ----------
    df
        Linelist; only confirmed DRC cases with a confirmation date are used
    window
        Moving average window in days
    date_limit
        Last date shown on the charts, defaults to the latest confirmation date
    slots
        Number of panels / health zones shown at once (at most ``len(PALETTE)``)
    columns
        Number of panels per row
    """
    return _area_cases(df, window, 2, date_limit, columns, slots, dropdowns=True)
