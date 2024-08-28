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
    ("data", get_counts),
    ("figure/epicurve", plot_epicurve),
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

OUTBREAKS = {"marburg": outbreak_marburg}
__all__ = ["OUTBREAKS"]
