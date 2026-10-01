"""Figuras Plotly: uma série por gráfico, cor única de destaque e zonas de limite discretas."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import LIMITS, MACHINE_BY_ID, VARIABLES

PALETTES = {
    "light": {"text": "#0F1B2D", "muted": "#5F6D80", "grid": "#E8ECF2", "surface": "#FFFFFF", "accent": "#00579D", "accent_fill": "rgba(0,87,157,0.08)",
              "other": "#C3CCD8", "ok": "#0ca30c", "warn": "#B26B00", "crit": "#d03b3b", "warn_fill": "rgba(250,178,25,0.16)", "crit_fill": "rgba(208,59,59,0.10)"},
    "dark": {"text": "#E8EEF7", "muted": "#8E9DB3", "grid": "#1E2B42", "surface": "#121B2C", "accent": "#4DA3E8", "accent_fill": "rgba(77,163,232,0.12)",
             "other": "#3A4A63", "ok": "#0ca30c", "warn": "#fab219", "crit": "#e66767", "warn_fill": "rgba(250,178,25,0.14)", "crit_fill": "rgba(230,103,103,0.14)"},
}


def pal(theme: str) -> dict:
    return PALETTES.get(theme or "light", PALETTES["light"])


def fmt(v, d=1) -> str:
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def style(fig: go.Figure, theme: str, height: int, hover: str = "x unified") -> go.Figure:
    p = pal(theme)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height, showlegend=False, hovermode=hover,
        font=dict(color=p["muted"], family="Inter, Segoe UI, system-ui, sans-serif", size=12), margin=dict(l=48, r=16, t=10, b=34),
        hoverlabel=dict(bgcolor=p["surface"], bordercolor=p["grid"], font=dict(color=p["text"], size=12)), uirevision="keep",
    )
    fig.update_xaxes(gridcolor=p["grid"], linecolor=p["grid"], zeroline=False, ticks="", tickfont=dict(color=p["muted"]))
    fig.update_yaxes(gridcolor=p["grid"], linecolor="rgba(0,0,0,0)", zeroline=False, ticks="", tickfont=dict(color=p["muted"]))
    return fig


def y_range(mtype: str, var: str, values) -> list[float]:
    lim = LIMITS[mtype][var]
    lo_ref = lim.get("crit_lo", lim["nominal"] * (0 if var == "vibration_mm_s" else 0.85))
    hi_ref = lim["crit_hi"]
    pad = (hi_ref - lo_ref) * 0.05
    vals = np.asarray(values, dtype=float)
    lo = min(float(vals.min()) if len(vals) else lo_ref, lo_ref) - pad
    hi = max(float(vals.max()) * 1.02 if len(vals) else hi_ref, hi_ref) + pad
    return [max(0.0, lo) if var == "vibration_mm_s" else lo, hi]


def add_zones(fig: go.Figure, mtype: str, var: str, theme: str) -> None:
    """Faixas de atenção/crítico: fundo discreto + rótulo curto à direita (cor + texto)."""
    p, lim, info = pal(theme), LIMITS[mtype][var], VARIABLES[var]
    d = info["decimals"] if var != "pressure_bar" else 0 if lim["nominal"] > 50 else 1
    yr = y_range(mtype, var, [])
    span = yr[1] - yr[0]
    top, bot = yr[1] + span, yr[0] - span
    fig.add_hrect(y0=lim["warn_hi"], y1=lim["crit_hi"], fillcolor=p["warn_fill"], line_width=0, layer="below")
    fig.add_hrect(y0=lim["crit_hi"], y1=top, fillcolor=p["crit_fill"], line_width=0, layer="below")
    marks = [(lim["warn_hi"], "Atenção", p["warn"], "dash"), (lim["crit_hi"], "Crítico", p["crit"], "solid")]
    if "warn_lo" in lim:
        fig.add_hrect(y0=lim["crit_lo"], y1=lim["warn_lo"], fillcolor=p["warn_fill"], line_width=0, layer="below")
        fig.add_hrect(y0=bot, y1=lim["crit_lo"], fillcolor=p["crit_fill"], line_width=0, layer="below")
        marks += [(lim["warn_lo"], "Atenção", p["warn"], "dash"), (lim["crit_lo"], "Crítico", p["crit"], "solid")]
    for y, text, color, dash in marks:
        fig.add_hline(y=y, line=dict(color=color, width=1, dash=dash))
        fig.add_annotation(xref="paper", x=1, y=y, text=f"{text} · {fmt(y, d)}", showarrow=False, xanchor="right", yanchor="bottom",
                           font=dict(size=11, color=color), xshift=-4)


def live_fig(machine: dict, var: str, t: list, y: list, theme: str, level: int) -> go.Figure:
    p, mtype, info = pal(theme), machine["type"], VARIABLES[var]
    fig = go.Figure()
    add_zones(fig, mtype, var, theme)
    fig.add_trace(go.Scatter(x=t, y=y, mode="lines", line=dict(color=p["accent"], width=2, shape="spline", smoothing=0.4),
                             hovertemplate="<b>%{y:.2f}</b> " + info["unit"] + "<extra></extra>"))
    if len(y):
        symbol = ["circle", "triangle-up", "square"][level]
        color = [p["accent"], p["warn"], p["crit"]][level]
        fig.add_trace(go.Scatter(x=[t[-1]], y=[y[-1]], mode="markers", hoverinfo="skip",
                                 marker=dict(size=11, symbol=symbol, color=color, line=dict(color=p["surface"], width=2))))
    fig.update_yaxes(range=y_range(mtype, var, y), title=None)
    return style(fig, theme, 400)


def trend_fig(df: pd.DataFrame, machine_id: str, var: str, rul: dict, theme: str, anomalies: pd.DataFrame) -> go.Figure:
    p, info = pal(theme), VARIABLES[var]
    mtype = MACHINE_BY_ID[machine_id]["type"]
    s = df[df["machine_id"] == machine_id].set_index("timestamp")[var]
    hourly = s.resample("1h").mean().dropna()
    fig = go.Figure()
    add_zones(fig, mtype, var, theme)
    fig.add_trace(go.Scatter(x=s.index, y=s, mode="lines", line=dict(color=p["accent"], width=1), opacity=0.28, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=hourly.index, y=hourly, mode="lines", line=dict(color=p["accent"], width=2),
                             hovertemplate="<b>%{y:.2f}</b> " + info["unit"] + " (média horária)<extra></extra>"))
    an = anomalies.reindex(s.index)["anomaly"].fillna(False).to_numpy(bool)
    pts = s[an]
    if len(pts):
        z = anomalies.reindex(pts.index)["z"].abs().sort_values(ascending=False).head(12).index
        pts = pts.loc[z]
        fig.add_trace(go.Scatter(x=pts.index, y=pts, mode="markers", marker=dict(size=9, symbol="circle-open", color=p["crit"], line=dict(width=2)),
                                 hovertemplate="Anomalia: <b>%{y:.2f}</b> " + info["unit"] + "<extra></extra>"))
    x_hi = s.index.max()
    if rul.get("fit") is not None and rul.get("target") is not None:
        t0, slope, icpt = rul["fit"]
        days_ahead = min(rul["rul_days"] + 2, 25) if rul["rul_days"] is not None else 7
        x_hi = s.index.max() + pd.Timedelta(days=days_ahead)
        xs = pd.date_range(s.index.max() - pd.Timedelta(days=3), x_hi, periods=40)
        ys = slope * ((xs - t0).total_seconds() / 86400.0) + icpt
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=p["accent"], width=2, dash="dot"), hoverinfo="skip"))
        if rul["rul_days"] is not None and rul["rul_days"] <= 60:
            cross = s.index.max() + pd.Timedelta(days=rul["rul_days"])
            fig.add_trace(go.Scatter(x=[cross], y=[rul["target"]], mode="markers", hoverinfo="skip",
                                     marker=dict(size=11, symbol="square", color=p["crit"], line=dict(color=p["surface"], width=2))))
            fig.add_annotation(x=cross, y=rul["target"], text=f"Limite crítico em ≈ {fmt(rul['rul_days'], 0)} d", showarrow=True, arrowhead=0, ax=-70, ay=44,
                               font=dict(size=12, color=p["text"]), bgcolor=p["surface"], bordercolor=p["grid"], borderpad=4, arrowcolor=p["grid"])
    fig.update_yaxes(range=y_range(mtype, var, s.to_numpy()))
    fig.update_xaxes(range=[s.index.min(), x_hi])
    return style(fig, theme, 400)


def health_fig(df: pd.DataFrame, theme: str) -> go.Figure:
    p = pal(theme)
    h = df.set_index("timestamp")["health_index"].resample("1h").mean().dropna()
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=45, fillcolor=p["crit_fill"], line_width=0, layer="below")
    fig.add_hrect(y0=45, y1=75, fillcolor=p["warn_fill"], line_width=0, layer="below")
    for y, text, color in ((75, "Atenção · 75", p["warn"]), (45, "Crítico · 45", p["crit"])):
        fig.add_hline(y=y, line=dict(color=color, width=1, dash="dash" if y == 75 else "solid"))
        fig.add_annotation(xref="paper", x=1, y=y, text=text, showarrow=False, xanchor="right", yanchor="bottom", font=dict(size=11, color=color), xshift=-4)
    fig.add_trace(go.Scatter(x=h.index, y=h, mode="lines", line=dict(color=p["accent"], width=2), fill="tozeroy", fillcolor=p["accent_fill"],
                             hovertemplate="Saúde <b>%{y:.0f}</b><extra></extra>"))
    fig.update_yaxes(range=[0, 102])
    return style(fig, theme, 400)


def compare_fig(health: dict[str, float], selected: str, theme: str) -> go.Figure:
    """Ênfase: a máquina escolhida em destaque, as demais em cinza."""
    p = pal(theme)
    items = sorted(health.items(), key=lambda kv: kv[1])
    ids = [i for i, _ in items]
    vals = [v for _, v in items]
    fig = go.Figure(go.Bar(y=ids, x=vals, orientation="h", marker=dict(color=[p["accent"] if i == selected else p["other"] for i in ids]),
                           text=[fmt(v, 0) for v in vals], textposition="outside", cliponaxis=False, textfont=dict(color=p["text"], size=12), width=0.5,
                           hovertemplate="%{y}: <b>%{x:.0f}</b><extra></extra>"))
    fig.update_xaxes(range=[0, 110], showgrid=True)
    fig.update_yaxes(showgrid=False)
    style(fig, theme, 400, hover="closest")
    fig.update_layout(margin=dict(l=60, r=30, t=10, b=34))
    return fig
