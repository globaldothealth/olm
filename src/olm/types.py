"Types used by olm"

import json
import dataclasses
from typing import Callable, Any, TypedDict, NotRequired, NamedTuple

import plotly.graph_objects as go

PlotFunction = Callable[..., dict[str, Any] | go.Figure]
PlotData = tuple[str, PlotFunction, dict[str, Any]]


class OutbreakInfo(TypedDict):
    id: str
    description: str
    schema: str
    plots: list[tuple[str, Callable[..., Any], dict[str, Any]]]
    additional_date_columns: NotRequired[list[str]]
    url: NotRequired[str]


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
