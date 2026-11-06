"Ebola BVD outbreak specific functions"

import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..plots import standard_plot_layout, standard_axis_layout, PALETTE

def html_ebola_bvd_country_counts(df: pd.DataFrame, global_args: dict, drc_new_cases: int, drc_new_deaths: int):
    """Generate HTML table of confirmed cases and deaths by country"""
    countries = df['Location_Admin0'].unique()
    last_report_ts = pd.to_datetime(global_args["last_report_end_date"], errors='coerce')

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



def plot_ebola_bvd_health_zone_barchart(df: pd.DataFrame, visible_zones: int = 15):
    """
    Creates stacked bar chart of Ebola BVD cases by health zone and outcome, with health zones grouped by Location Admin1.

    There are too many health zones to fit, so only the first `visible_zones` (the ones with the most cases) are
    in view initially. A plotly range slider below the chart is always visible and is used to scroll through the
    rest (drag the selection, or its edges to zoom).
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
        height=540,  # room for the tick labels and the range slider
        margin={"l": 0, "r": 0, "t": 5, "b": 35},
        legend={"x": 0.9, "y": 0.9, "xanchor": "right"},
    )
    fig.update_xaxes(
        title='Health zone',
        tickmode='array',
        tickvals=order,
        ticktext=[tick_text_map.get(label, label) for label in order],
        range=[-0.5, min(visible_zones, len(order)) - 0.5],
        rangeslider={"visible": True, "thickness": 0.08},
    )
    fig.update_yaxes(title='Case count')
    return fig


MOVING_AVERAGE_DAYS = 7
PANEL_COLUMNS = 2


def _area_moving_averages(df: pd.DataFrame, column: str, date_limit: str | None):
    """Daily confirmed DRC cases per area (value of `column`) over the whole outbreak span, and their trailing
    `MOVING_AVERAGE_DAYS` moving average (over fewer days at the very start).

    Returns ``(totals, x, y, daily)``: confirmed case totals per area (highest first), the dates as ``YYYY-MM-DD``
    strings, and dicts mapping each area to its moving average and to its daily case counts.
    """
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
    y = {
        area: counts.rolling(MOVING_AVERAGE_DAYS, min_periods=1).mean().round(1).tolist()
        for area, counts in daily.items()
    }
    return totals, x, y, {area: counts.tolist() for area, counts in daily.items()}


def _panel(i: int) -> dict:
    return {"row": i // PANEL_COLUMNS + 1, "col": i % PANEL_COLUMNS + 1}


def _area_cases(x: list[str], y: dict, daily: dict, areas: list[str], top: int, titles: list[str] | None = None):
    """Grid of panels, one per area in `areas`: daily cases as bars behind the moving average line, date and y
    axis labels on every panel, one shared y scale and the full date range. Traces ``0..n-1`` are the lines and
    ``n..2n-1`` the bars. `top` is the room above the grid for titles and controls.
    """
    n = len(areas)
    rows = -(-n // PANEL_COLUMNS)  # ceil
    row_px = 300  # panel height including the date labels below it and the title or dropdown above it
    fig = make_subplots(rows=rows, cols=PANEL_COLUMNS, horizontal_spacing=0.12,
                        vertical_spacing=120 / (row_px * rows), subplot_titles=titles)
    for annotation in fig.layout.annotations:
        annotation.font = {"size": 14}
    for i, area in enumerate(areas):
        fig.add_trace(go.Scatter(x=x, y=y[area], name=f"{MOVING_AVERAGE_DAYS}-day average", line_color=PALETTE[0],
                                 line_width=2), **_panel(i))
    for i, area in enumerate(areas):  # plotly always draws bars below lines
        fig.add_trace(go.Bar(x=x, y=daily[area], name="Daily cases", marker_color=PALETTE[0], opacity=0.35),
                      **_panel(i))
    fig.update_xaxes(**standard_axis_layout, range=[x[0], x[-1]], dtick="M1", tickformat="%b<br>%Y",
                     title_text="Date of confirmation")
    fig.update_yaxes(**standard_axis_layout, zeroline=False, matches="y", rangemode="tozero",
                     title_text=f"Daily cases and {MOVING_AVERAGE_DAYS}-day average")
    fig.update_layout(**standard_plot_layout, showlegend=False, bargap=0.1, height=row_px * rows + top,
                      margin={"l": 0, "r": 0, "t": top, "b": 0})
    return fig


def _zone_dropdown(slot: int, n: int, totals: pd.Series, dates: list[str], averages: dict, daily: dict,
                   **position) -> dict:
    """Plotly dropdown which shows the chosen health zone in panel `slot` of `_area_cases` by swapping the data
    of its line and bars. Options are "None" (hides the panel's traces) and every zone with its total cases.
    """
    traces = [slot, slot + n]
    buttons = [{"label": "None", "method": "restyle", "args": [{"visible": [False, False]}, traces]}] + [
        {"label": f"{zone} ({count:,})", "method": "restyle",
         "args": [{"x": [dates, dates], "y": [averages[zone], daily[zone]], "visible": [True, True]},
                  traces]}
        for zone, count in totals.items()
    ]
    return {"type": "dropdown", "direction": "down", "showactive": True, "xanchor": "left", "yanchor": "bottom",
            "borderwidth": 0, "bgcolor": "#fff", "buttons": buttons, **position}


def plot_province_cases(df: pd.DataFrame, global_args: dict):
    """Panel per DRC province, titled with its total of confirmed cases, see `_area_cases`. "Plot scale" buttons
    switch between one shared y scale (absolute) and one per panel (relative), as small provinces are unreadable
    on the shared one.
    """
    totals, x, y, daily = _area_moving_averages(df, "Location Admin1", global_args.get("report_end_date"))
    areas = totals.index.tolist()
    top = 90  # room for the panel titles and the scale buttons above them
    fig = _area_cases(x, y, daily, areas, top, titles=[f"{area} ({totals[area]:,})" for area in areas])
    yaxes = ["yaxis"] + [f"yaxis{k}" for k in range(2, len(areas) + 1)]
    scale = lambda matches: [{**{f"{a}.matches": matches for a in yaxes}, **{f"{a}.autorange": True for a in yaxes}}]
    buttons_y = 1 + (top - 10) / fig.layout.height
    # plotly sizes the buttons (about 127px) and overshoots the right edge (hence `pad`); the label is 8px left
    fig.add_annotation(text="Plot scale:", xref="paper", yref="paper", x=1, y=buttons_y, xanchor="right",
                       yanchor="top", yshift=-6, xshift=-145, showarrow=False, font={"size": 13})
    fig.update_layout(updatemenus=[{
        "type": "buttons", "direction": "right", "showactive": True, "active": 0, "bgcolor": "#fff",
        "x": 1, "xanchor": "right", "y": buttons_y, "yanchor": "top", "pad": {"r": 4},
        "buttons": [
            {"label": "absolute", "method": "relayout", "args": scale("y")},
            {"label": "relative", "method": "relayout", "args": scale(None)},
        ],
    }])
    return fig


def plot_health_zone_cases(df: pd.DataFrame, global_args: dict, slots: int = 4):
    """Panels for `slots` DRC health zones, starting with those with the most confirmed cases, see `_area_cases`.
    A "Health Zone:" dropdown above each panel switches it to any health zone. Plotly dropdowns are stateless, so
    a zone picked in one panel is still offered in the others.
    """
    totals, x, y, daily = _area_moving_averages(df, "Health zone", global_args.get("report_end_date"))
    areas = totals.index[:slots].tolist()
    fig = _area_cases(x, y, daily, areas, top=50)
    menus = []
    for i in range(len(areas)):
        subplot = fig.get_subplot(**_panel(i))
        left, bottom = subplot.xaxis.domain[0], subplot.yaxis.domain[1] + 0.01
        fig.add_annotation(text="Health Zone:", xref="paper", yref="paper", x=left, y=bottom, xanchor="left",
                           yanchor="bottom", yshift=8, xshift=-10, showarrow=False, font={"size": 14})
        # pad moves the dropdown right, past the label
        menus.append(_zone_dropdown(i, len(areas), totals, x, y, daily, x=left, y=bottom, active=i + 1,
                                    pad={"l": 80}, font={"size": 14}))
    fig.update_layout(updatemenus=menus)
    return fig
