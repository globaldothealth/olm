from typing import Callable, Any, TypedDict, NotRequired
import plotly.graph_objects as go

PlotFunction = Callable[..., dict[str, Any] | go.Figure]
PlotData = tuple[str, PlotFunction, dict[str, Any]]


class OutbreakInfo(TypedDict):
    id: str
    description: str
    plots: list[tuple[str, Callable[..., Any], dict[str, Any]]]
    additional_date_columns: NotRequired[list[str]]
    url: NotRequired[str]
