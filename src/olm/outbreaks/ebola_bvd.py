"Ebola BVD outbreak specific functions"

import pandas as pd
import plotly.express as px

from ..plots import standard_plot_layout, PALETTE

def html_ebola_bvd_country_counts(df: pd.DataFrame, last_report_date: str, drc_new_cases: int, drc_new_deaths: int):
    """Generate HTML table of confirmed cases and deaths by country"""
    countries = df['Location_Admin0'].unique()
    last_report_ts = pd.to_datetime(last_report_date, errors='coerce')
    print(last_report_ts)

    def render_stat_cell(title: str, icon: str, new_count: int, total_count: int) -> str:
        """Helper to render a stat cell with icon and counts"""
        return (
            '<td class="without-border">'
            f'<h3>{title}</h3><br/>'
            f'<img id="confirmed_img" src="images/{icon}{"_new" if new_count > 0 else ""}.png">'
            '<br/>'
            f'<span class="outbreak-summary-values">New: <strong>{new_count}</strong> <br/>Total: <strong>{total_count}</strong></span>'
            '</td>'
        )

    rows = []
    for country in countries:
        country_df = df[df['Location_Admin0'] == country]
        confirmed = country_df[country_df['Case_status'] == 'confirmed']

        # Calculate confirmed cases counts
        date_confirmation = pd.to_datetime(confirmed['Date_confirmation'], errors='coerce')
        new_confirmed_count = int((date_confirmation > last_report_ts).sum())

        confirmed_count = len(confirmed)

        # Calculate confirmed deaths counts
        confirmed_deaths_count = len(confirmed[confirmed['Outcome'] == 'Death'])
        date_death = pd.to_datetime(country_df['Date_death'], errors='coerce')
        new_confirmed_deaths_mask = (country_df['Outcome'] == 'Death') & (date_death > last_report_ts)
        new_confirmed_deaths_count = int(new_confirmed_deaths_mask.sum())

        # Use variable numbers for DRC
        if country == "Democratic Republic of the Congo":
            new_confirmed_count = drc_new_cases
            new_confirmed_deaths_count = drc_new_deaths

        # Build row
        cases_cell = render_stat_cell('Confirmed Cases', 'confirmed', new_confirmed_count, confirmed_count)
        deaths_cell = render_stat_cell('Confirmed Deaths', 'dead', new_confirmed_deaths_count, confirmed_deaths_count)
        row = f'<thead><td colspan=2 align="left"><h3>{country}</h3></td></thead><tr>{cases_cell}{deaths_cell}</tr>'
        rows.append(row)

    return '<table class="summary-table">' + ''.join(rows) + '</table>'

def plot_ebola_bvd_health_zone_barchart(df: pd.DataFrame):
    """
    Creates stacked bar chart of Ebola BVD cases by health zone and outcome, with health zones grouped by Location Admin1.
    """
    df = df.copy()
    df = df[df["Location_Admin0"] == "Democratic Republic of the Congo"]
    df = df[(df["Case_status"] == 'confirmed') | (df["Case_status"] == 'a ventiler')]
    y_values = df['Health zone']
    y_empty_mask = y_values.isna() | (y_values.astype(str).str.strip() == "")
    df.loc[y_empty_mask, 'Health zone'] = "Other"

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
            if str(row['Health zone']).strip().lower() == "other"
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
