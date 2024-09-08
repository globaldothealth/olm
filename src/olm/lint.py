"""
olm lint and quality control module
"""

from pathlib import Path

import pandas as pd

from .types import LintResult
from .outbreaks import read_outbreak, read_schema

import fastjsonschema


def lint(outbreak: str, file: str | None = None) -> LintResult:
    errors = []
    # do not convert dates as fastjsonschema will check date string representation
    df = read_outbreak(outbreak, file, convert_dates=False)
    schema = read_schema(Path("GHL2024.D11.1E71.schema.json"))
    validator = fastjsonschema.compile(schema)

    for row in df.to_dict("records"):
        id = row["ID"]
        nrow = {k: v for k, v in row.items() if pd.notnull(v)}
        try:
            validator(nrow)
        except fastjsonschema.JsonSchemaValueException as e:
            print(f"ID {id}: {e}, found: {nrow[e.path[1]]}")
    return LintResult(outbreak, schema, "", len(errors) == 0, errors)
