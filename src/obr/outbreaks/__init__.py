"""
Outbreak configurations
"""

from ..plots import (
    get_counts,
    plot_epicurve,
    plot_timeseries_location_status,
    plot_age_gender,
    plot_delay_distribution,
)

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
    ("data", get_counts, dict(date_col="Date_entry")),
    (
        "figure/epicurve_source_report",
        plot_epicurve,
        {
            "title": "Date of report in primary source",
            "date_col": "Source_I_Date report",
            "groupby_col": "Case_status",
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

OUTBREAKS = {
    "marburg": {"plots": outbreak_marburg, "additional_date_columns": ["Data_up_to"]},
    "mpox-2024": {"plots": outbreak_mpox_2024},
}
__all__ = ["OUTBREAKS"]
