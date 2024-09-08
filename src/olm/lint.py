"""
olm lint and quality control module
"""

import json
import dataclasses
from typing import NamedTuple


from .outbreaks import read_outbreak


class RowError(NamedTuple):
    id: str
    column: str
    value: str
    message: str


@dataclasses.dataclass
class LintResult:
    outbreak: str
    schema: str
    filehash: str
    ok: bool
    errors: list[RowError]

    def as_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), sort_keys=True, indent=2)

    def as_html(self) -> str:
        pass

    def as_slack(self) -> str:
        pass


def lint(outbreak: str, file: str | None = None) -> LintResult:
    errors = []
    schema = None
    df = read_outbreak(outbreak, file)
    for row in df.to_dict("records"):
        # lint each row
        pass
    return LintResult(outbreak, schema, "", len(errors) == 0, errors)
