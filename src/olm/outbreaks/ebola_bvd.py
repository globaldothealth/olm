"Ebola BVD outbreak specific functions"

import html

import pandas as pd
import plotly.express as px

from ..plots import standard_plot_layout, PALETTE

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
    # caption = (
    #     '<caption class="country-counts-notes">'
    #     '<sup>*</sup> Deaths include confirmed cases not yet assigned to a health zone ("a ventiler"). '
    #     '<sup>&dagger;</sup> Case fatality ratio: confirmed deaths / confirmed cases (incl. "a ventiler").'
    #     '</caption>'
    # )
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
