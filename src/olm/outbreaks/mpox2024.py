"Mpox 2024 outbreak specific functions"

import pandas as pd

from ..plots import get_aggregate
from ..sources import source_google_sheet


def mpox_2024_aggregate(linelist: pd.DataFrame) -> pd.DataFrame:
    agg = (
        get_aggregate(
            linelist,
            "Location_Admin0",
            [("Case_status", "confirmed"), ("Outcome", "death")],
        )
        .rename(
            columns={
                "Location_Admin0": "Country",
                "confirmed": "Confirmed cases",
                "death": "Confirmed deaths",
            }
        )
        .sort_values("Confirmed cases", ascending=False)
    ).set_index("Country")
    death_data = source_google_sheet(None, "index", 2)  # third sheet is deaths data
    death_data = death_data.set_index(death_data.columns[0])

    # Retrieve death data for DRC, which is the last column
    drc_deaths = int(death_data.loc["Democratic Republic of the Congo"].iloc[-2])
    agg.loc["Democratic Republic of the Congo", "Confirmed deaths"] = drc_deaths
    return agg.reset_index()
