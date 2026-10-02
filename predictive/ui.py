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


def tip(label, text: str, align: str = "left"):
    """Rótulo com ícone 'i' e dica contextual (hover/foco). align: 'left' ou 'right' (evita estourar a borda)."""
    return html.Span([label, html.Span("i", className="tip-i", **{"aria-hidden": "true"})], className=f"tip {align}", tabIndex=0,
                     **{"data-tip": text, "aria-label": f"{label if isinstance(label, str) else ''}: {text}"})


TIPS = {
    "vibration_mm_s": "Quanto a máquina “treme” (velocidade de vibração, em mm/s). Valores altos podem indicar rolamento desgastado, desalinhamento ou desbalanceamento.",
    "temperature_c": "Calor da máquina, em °C. Aumento constante pode indicar atrito, falta de lubrificação ou resfriamento deficiente.",
    "pressure_bar": "Pressão do óleo ou do ar, em bar. Queda pode indicar vazamento; valor muito alto, risco de sobrecarga.",
    "health": "Nota de 0 a 100 que resume o quão perto a máquina está dos limites. Quanto menor, pior. Combina as três variáveis (a vibração pesa mais).",
    "state": "Normal: dentro da faixa. Atenção: passou do limite de atenção. Crítico: passou do limite crítico. O estado usa cor, forma e texto.",
    "rul": "Estimativa de dias até a variável chegar ao limite crítico, se a tendência dos últimos 5 dias continuar. É um modelo didático (uma reta).",
    "trend": "Calculada a partir da evolução dos últimos 5 dias de leituras.",
    "confidence": "Mede o quanto os dados seguem uma reta (R²). Confiança baixa significa que a estimativa é pouco confiável.",
    "zones": "A faixa amarela marca a zona de atenção e a vermelha, a zona crítica. As linhas mostram os limites.",
    "slope": "Quanto a variável aumenta (ou diminui) por dia, em média, nos últimos 5 dias.",
}
