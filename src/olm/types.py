"Types used by olm"

import json
import dataclasses
from typing import Callable, Any, NamedTuple

import plotly.graph_objects as go

PlotFunction = Callable[..., dict[str, Any] | go.Figure]
PlotData = tuple[str, PlotFunction, dict[str, Any]]


class RowError(NamedTuple):
    id: str
    column: str
    value: str
    message: str


@dataclasses.dataclass
class LintResult:
    outbreak: str
    schema: str
    ok: bool
    errors: list[RowError]

    def as_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), sort_keys=True, indent=2)

    def __str__(self) -> str:
        return "\n".join(
            f"- ID {e.id}: {e.message}, found={e.value}" for e in self.errors
        )

    def as_html(self) -> str:
        pass

    def as_slack(self) -> str:
        header = (
            "✅ Lint succeeded for " if self.ok else "❌ Lint failed for "
        ) + f"*{self.outbreak}*"
        if self.ok:
            return header
        errors = "\n".join(
            f"- ID {e.id}: {e.message}, found={e.value}" for e in self.errors
        )
        return header + "\n" + errors
