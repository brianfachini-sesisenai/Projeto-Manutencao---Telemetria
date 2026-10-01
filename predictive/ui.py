"""Componentes de interface reutilizáveis."""
from __future__ import annotations

from dash import dcc, html

from .config import MACHINES, STATUS_LABEL, VARIABLES


def chip(level: int | None, text: str | None = None, neutral: bool = False):
    cls = "chip neutral" if neutral or level is None else f"chip s{level}"
    return html.Span(text or STATUS_LABEL[level or 0], className=cls)


def seg(id_: str, options: list[tuple[str, str]] | list[tuple], value, **kw):
    """Controle segmentado (rádio estilizado). options = [(valor, rótulo)]."""
    return dcc.RadioItems(id=id_, className="seg", value=value, inline=True, persistence=False,
                          options=[{"label": html.Span(lab, className="seg-lab"), "value": val} for val, lab in options], **kw)


def machine_seg(id_: str, value: str):
    return dcc.RadioItems(id=id_, className="seg", value=value, inline=True,
                          options=[{"label": html.Span(m["machine_id"], className="seg-lab", title=m["name"]), "value": m["machine_id"]} for m in MACHINES])


def page_head(title: str, sub: str, right=None):
    return html.Div([html.Div([html.H1(title, className="page-title"), html.P(sub, className="page-sub")]), right or html.Div()], className="page-head")


def details(summary: str, *children, open_: bool = False):
    return html.Details([html.Summary(summary), html.Div(list(children), className="more-body")], className="more", open=open_)


VAR_TABS = [(k, v["label"]) for k, v in VARIABLES.items()]
