"""
Custom sources of data
"""

import os
from pathlib import Path

import pygsheets
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd

DOWNLOADS = Path(os.getenv("OBT_DOWNLOAD_FOLDER", Path.home() / "Downloads"))


def source_google_sheet(_, ws_property: str, ws_value: str | int) -> pd.DataFrame:
    "A Google sheet source"
    if (document_key := os.getenv("OLM_SRC_GOOGLE_SHEET_ID")) is None:
        raise ValueError("No Google sheet specified in OLM_SRC_GOOGLE_SHEET_ID")
    if os.getenv("OLM_SRC_GOOGLE_SHEET_CREDENTIALS") is None:
        raise ValueError(
            "source_google_sheet requires credentials set in OLM_SRC_GOOGLE_SHEET_CREDENTIALS"
        )
    client = pygsheets.authorize(
        service_account_env_var="OLM_SRC_GOOGLE_SHEET_CREDENTIALS"
    )
    spreadsheet = client.open_by_key(document_key)
    return spreadsheet.worksheet(ws_property, ws_value).get_as_df(numerize=False)


def source_databutton(
    _,
    link: str,
    button_text: str,
    download_folder: Path = DOWNLOADS,
    cleanup: bool = True,
) -> pd.DataFrame:
    options = webdriver.FirefoxOptions()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.get(link)

    def find_button(text):
        if not (
            elems := [
                e for e in driver.find_elements(By.TAG_NAME, "button") if text in e.text
            ]
        ):
            raise ValueError(f"No button found with {text}")
        return elems[0]

    find_button(button_text).click()
    file = max(
        map(lambda file: download_folder / file, os.listdir(download_folder)),
        key=os.path.getctime,
    )
    if file.suffix != ".csv":
        raise ValueError(
            "source_databutton(): Only CSV files are supported at the moment"
        )
    df = pd.read_csv(file)
    if cleanup:
        os.remove(file)
    return df
