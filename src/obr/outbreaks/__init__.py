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
    ("data", get_counts, dict(date_col="Data_up_to")),
    (
        "figure/epicurve",
        plot_epicurve,
        dict(
            title="Date of symptom onset",
            date_col="Date_onset_estimated",
            groupby_col="Case_status",
        ),
    ),
    (
        "figure/epicurve_location_status",
        plot_timeseries_location_status,
        dict(admin_column="Location_District"),
    ),
    ("figure/age_gender", plot_age_gender),
    (
        "figure/delay_distribution_consult",
        plot_delay_distribution,
        dict(
            col="Date_of_first_consult",
            title="Delay to consultation from onset",
            index="A",
            max_delay_days=20,
        ),
    ),
    (
        "figure/delay_distribution_death",
        plot_delay_distribution,
        dict(
            col="Date_death",
            title="Delay to death from onset",
            index="B",
            max_delay_days=20,
        ),
    ),
]

outbreak_mpox_2024 = [
    ("data", get_counts, dict(date_col="Date_entry")),
    ("figure/epicurve", plot_epicurve),
]
OUTBREAKS = {"marburg": outbreak_marburg, "mpox-2024": outbreak_mpox_2024}
__all__ = ["OUTBREAKS"]
