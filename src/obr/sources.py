"""
Custom sources of data
"""

import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd

DOWNLOADS = Path(os.getenv("OBT_DOWNLOAD_FOLDER", Path.home() / "Downloads"))


def source_databutton(
    link: str, button_text: str, download_folder: Path = DOWNLOADS
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
        else:
            print(text)
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
    return pd.read_csv(file)
