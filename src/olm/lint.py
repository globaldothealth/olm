"""
olm lint and quality control module
"""

from pathlib import Path

import pandas as pd

from .types import LintResult, RowError
from .outbreaks import read_outbreak, read_schema, get_schema_url

import fastjsonschema


def lint(
    outbreak: str,
    file: str | None = None,
    schema_path: str | Path | None = None,
    ignore_fields: list[str] = [],
) -> LintResult:
    errors: list[RowError] = []
    # do not convert dates as fastjsonschema will check date string representation
    df = read_outbreak(outbreak, file, convert_dates=False)
    if (schema_url := schema_path or get_schema_url(outbreak)) is None:
        raise ValueError("No schema_path passed or schema url found in OUTBREAKS")
    schema = read_schema(schema_url)
    validator = fastjsonschema.compile(schema)

    for row in df.to_dict("records"):
        id = row["ID"]
        nrow = {
            k: v for k, v in row.items() if pd.notnull(v) and k not in ignore_fields
        }
        try:
            validator(nrow)
        except fastjsonschema.JsonSchemaValueException as e:
            column = e.path[1]
            errors.append(RowError(id, column, nrow[column], e.message))
    return LintResult(outbreak, str(schema_url), len(errors) == 0, errors)
