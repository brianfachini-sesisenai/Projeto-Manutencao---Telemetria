"""Construção das figuras Plotly (todas as cores vêm da paleta do tema ativo)."""
from __future__ import annotations

from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .analytics import level_of
from .config import LIMITS, MACHINE_BY_ID, MACHINE_IDS, STATUS_LABEL, VAR_KEYS, VARIABLES

PALETTES = {
    "light": {
        "text": "#1F2A37", "muted": "#5B6776", "grid": "#E3E8EF", "bg": "rgba(0,0,0,0)",
        "blue": "#00579D", "vib": "#00579D", "temperature_c": "#D9560B", "pressure_bar": "#0F8B8D",
        "warn": "#B7791F", "crit": "#C62828", "ok": "#2E7D32", "warn_fill": "rgba(242,169,0,0.10)",
        "crit_fill": "rgba(198,40,40,0.10)", "accent2": "#7A5AF8",
    },
    "dark": {
        "text": "#E6EDF5", "muted": "#9AA8B8", "grid": "#2A3948", "bg": "rgba(0,0,0,0)",
        "blue": "#4DA3E8", "vib": "#4DA3E8", "temperature_c": "#FF8A3D", "pressure_bar": "#3CC4C6",
        "warn": "#F2B84B", "crit": "#FF6B6B", "ok": "#5CCB7A", "warn_fill": "rgba(242,184,75,0.12)",
        "crit_fill": "rgba(255,107,107,0.13)", "accent2": "#A18AFF",
    },
}
VAR_COLOR_KEY = {"vibration_mm_s": "vib", "temperature_c": "temperature_c", "pressure_bar": "pressure_bar"}


def pal(theme: str) -> dict:
    return PALETTES.get(theme or "light", PALETTES["light"])


def fmt(v, d=1) -> str:
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def style(fig: go.Figure, theme: str, height: int | None = None, legend: bool = False) -> go.Figure:
    p = pal(theme)
    fig.update_layout(
        paper_bgcolor=p["bg"], plot_bgcolor=p["bg"], font=dict(color=p["text"], family="Inter, Segoe UI, system-ui, sans-serif", size=12),
        margin=dict(l=52, r=16, t=28, b=36), hovermode="x unified", showlegend=legend,
        legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)"), height=height,
        hoverlabel=dict(font_size=12), uirevision="keep",
    )
    fig.update_xaxes(gridcolor=p["grid"], zerolinecolor=p["grid"], linecolor=p["grid"], tickfont=dict(color=p["muted"]))
    fig.update_yaxes(gridcolor=p["grid"], zerolinecolor=p["grid"], linecolor=p["grid"], tickfont=dict(color=p["muted"]))
    return fig


def empty_fig(theme: str, msg: str = "Aguardando telemetria…", height: int = 260) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=pal(theme)["muted"]))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style(fig, theme, height)


def y_range(mtype: str, var: str, values) -> list[float]:
    lim = LIMITS[mtype][var]
    lo_ref = lim.get("crit_lo", lim["nominal"] * 0.85 if var != "vibration_mm_s" else 0)
    hi_ref = lim["crit_hi"]
    vmin, vmax = (float(np.min(values)), float(np.max(values))) if len(values) else (lo_ref, hi_ref)
    pad = (hi_ref - lo_ref) * 0.06
    lo = min(vmin, lo_ref) - pad
    if var == "vibration_mm_s":
        lo = max(0, lo)
    return [lo, max(vmax * 1.03, hi_ref) + pad]


def add_zones(fig: go.Figure, mtype: str, var: str, theme: str, row=None, col=None, label: bool = True) -> None:
    """Faixas de atenção/crítico e linhas de limite (redundância visual: cor + traço + rótulo)."""
    p, lim = pal(theme), LIMITS[mtype][var]
    yr = y_range(mtype, var, [])
    kw = dict(row=row, col=col) if row else {}
    top = yr[1] + (yr[1] - yr[0])
    fig.add_hrect(y0=lim["warn_hi"], y1=lim["crit_hi"], fillcolor=p["warn_fill"], line_width=0, layer="below", **kw)
    fig.add_hrect(y0=lim["crit_hi"], y1=top, fillcolor=p["crit_fill"], line_width=0, layer="below", **kw)
    fig.add_hline(y=lim["warn_hi"], line=dict(color=p["warn"], width=1.2, dash="dash"), **kw,
                  annotation_text="Atenção" if label else None, annotation_position="bottom right",
                  annotation_font=dict(size=10, color=p["warn"]))
    fig.add_hline(y=lim["crit_hi"], line=dict(color=p["crit"], width=1.2, dash="dot"), **kw,
                  annotation_text="Crítico" if label else None, annotation_position="bottom right",
                  annotation_font=dict(size=10, color=p["crit"]))
    if "warn_lo" in lim:
        bot = yr[0] - (yr[1] - yr[0])
        fig.add_hrect(y0=lim["crit_lo"], y1=lim["warn_lo"], fillcolor=p["warn_fill"], line_width=0, layer="below", **kw)
        fig.add_hrect(y0=bot, y1=lim["crit_lo"], fillcolor=p["crit_fill"], line_width=0, layer="below", **kw)
        fig.add_hline(y=lim["warn_lo"], line=dict(color=p["warn"], width=1.2, dash="dash"), **kw)
        fig.add_hline(y=lim["crit_lo"], line=dict(color=p["crit"], width=1.2, dash="dot"), **kw)


def telemetry_fig(machine: dict, data: dict, theme: str) -> go.Figure:
    """3 painéis empilhados (vibração, temperatura, pressão) com zonas de limite."""
    mtype = machine["type"]
    p = pal(theme)
    keys = {"vibration_mm_s": "vib", "temperature_c": "temp", "pressure_bar": "press"}
    titles = [f"{VARIABLES[v]['label']} ({VARIABLES[v]['unit']})" for v in VAR_KEYS]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07, subplot_titles=titles)
    for i, var in enumerate(VAR_KEYS, start=1):
        y = data[keys[var]]
        fig.add_trace(go.Scatter(x=data["t"], y=y, mode="lines", name=VARIABLES[var]["label"],
                                 line=dict(color=p[VAR_COLOR_KEY[var]], width=2),
                                 hovertemplate="%{y:.2f} " + VARIABLES[var]["unit"]), row=i, col=1)
        if len(y):
            lvl = level_of(mtype, var, y[-1])
            fig.add_trace(go.Scatter(x=[data["t"][-1]], y=[y[-1]], mode="markers", showlegend=False, hoverinfo="skip",
                                     marker=dict(size=10, color=[p["ok"], p["warn"], p["crit"]][lvl],
                                                 symbol=["circle", "triangle-up", "square"][lvl],
                                                 line=dict(color=p["text"], width=1))), row=i, col=1)
        add_zones(fig, mtype, var, theme, row=i, col=1)  # após os traços: subplots vazios ignoram shapes
        fig.update_yaxes(range=y_range(mtype, var, y), row=i, col=1)
    fig.update_annotations(font=dict(size=12, color=p["muted"]), xanchor="left", x=0)
    style(fig, theme, 640)
    fig.update_layout(margin=dict(l=56, r=16, t=30, b=36))
    return fig


def heatmap_fig(snapshot: dict, theme: str) -> go.Figure:
    """Severidade (fração do caminho nominal -> crítico) por máquina x variável."""
    from .analytics import exceed_score
    p = pal(theme)
    z, text = [], []
    for mid in MACHINE_IDS:
        m = snapshot["machines"].get(mid)
        mtype = MACHINE_BY_ID[mid]["type"]
        row_z, row_t = [], []
        for var, key in (("vibration_mm_s", "vib"), ("temperature_c", "temp"), ("pressure_bar", "press")):
            v = m[key][-1] if m and m[key] else np.nan
            row_z.append(min(exceed_score(mtype, var, v), 1.2) if m else np.nan)
            row_t.append(f"{fmt(v, VARIABLES[var]['decimals'])} {VARIABLES[var]['unit']}")
        z.append(row_z)
        text.append(row_t)
    scale = [[0, p["ok"]], [0.30, p["ok"]], [0.43, p["warn"]], [0.80, p["warn"]], [0.84, p["crit"]], [1, p["crit"]]]
    fig = go.Figure(go.Heatmap(
        z=z, x=[VARIABLES[v]["label"] for v in VAR_KEYS], y=MACHINE_IDS, text=text, texttemplate="%{text}",
        colorscale=scale, zmin=0, zmax=1.2, xgap=3, ygap=3, showscale=False, hoverinfo="skip",
        textfont=dict(color="#FFFFFF" if theme == "dark" else "#FFFFFF", size=12),
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top")
    style(fig, theme, 300)
    fig.update_layout(margin=dict(l=60, r=8, t=30, b=8), hovermode=False)
    return fig


def sparkline_uri(values: list[float], color: str, width: int = 160, height: int = 30) -> str:
    if len(values) < 2:
        return ""
    v = np.asarray(values[-90:], dtype=float)
    lo, hi = float(v.min()), float(v.max())
    span = (hi - lo) or 1.0
    xs = np.linspace(1, width - 1, len(v))
    ys = height - 3 - (v - lo) / span * (height - 6)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
           f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='1.6' stroke-linejoin='round'/></svg>")
    return "data:image/svg+xml;utf8," + quote(svg)


def health_fig(df: pd.DataFrame, theme: str) -> go.Figure:
    p = pal(theme)
    d = df.set_index("timestamp")["health_index"]
    hourly = d.resample("1h").mean().dropna()
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=45, fillcolor=p["crit_fill"], line_width=0, layer="below")
    fig.add_hrect(y0=45, y1=75, fillcolor=p["warn_fill"], line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=d.index, y=d, mode="lines", name="Leitura (10 min)", line=dict(color=p["muted"], width=1), opacity=0.5))
    fig.add_trace(go.Scatter(x=hourly.index, y=hourly.rolling(6, min_periods=1).mean(), mode="lines", name="Média móvel (6 h)",
                             line=dict(color=p["blue"], width=2.6)))
    fig.add_hline(y=75, line=dict(color=p["warn"], dash="dash", width=1), annotation_text="Atenção < 75", annotation_position="bottom left",
                  annotation_font=dict(size=10, color=p["warn"]))
    fig.add_hline(y=45, line=dict(color=p["crit"], dash="dot", width=1), annotation_text="Crítico < 45", annotation_position="bottom left",
                  annotation_font=dict(size=10, color=p["crit"]))
    fig.update_yaxes(range=[0, 102], title_text="Índice de saúde")
    return style(fig, theme, 300, legend=True)


def trend_fig(df: pd.DataFrame, machine_id: str, var: str, rul: dict, theme: str, anomalies: pd.DataFrame, horizon_days: int = 14) -> go.Figure:
    p = pal(theme)
    mtype = MACHINE_BY_ID[machine_id]["type"]
    info, lim = VARIABLES[var], LIMITS[mtype][var]
    d = df[df["machine_id"] == machine_id].set_index("timestamp")[var]
    fig = go.Figure()
    add_zones(fig, mtype, var, theme)
    fig.add_trace(go.Scatter(x=d.index, y=d, mode="lines", name="Leitura", line=dict(color=p[VAR_COLOR_KEY[var]], width=1.2), opacity=0.75))
    an = anomalies.reindex(d.index)
    pts = d[an["anomaly"].fillna(False).to_numpy(bool)]
    if len(pts):
        fig.add_trace(go.Scatter(x=pts.index, y=pts, mode="markers", name="Anomalia (z robusto > 3,5)",
                                 marker=dict(size=9, symbol="diamond-open", color=p["crit"], line=dict(width=2))))
    if rul.get("fit") is not None:
        t0, slope, intercept = rul["fit"]
        end = d.index.max() + pd.Timedelta(days=horizon_days)
        xs = pd.date_range(t0, end, periods=60)
        ys = slope * ((xs - t0).total_seconds() / 86400.0) + intercept
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Tendência (regressão linear)", line=dict(color=p["accent2"], width=2.4, dash="dash")))
    fig.update_yaxes(range=y_range(mtype, var, d.to_numpy()), title_text=f"{info['label']} ({info['unit']})")
    return style(fig, theme, 360, legend=True)


def box_fig(df: pd.DataFrame, var: str, theme: str) -> go.Figure:
    p = pal(theme)
    fig = go.Figure()
    for mid in MACHINE_IDS:
        d = df[df["machine_id"] == mid][var]
        fig.add_trace(go.Box(y=d, name=mid, marker_color=p[VAR_COLOR_KEY[var]], line=dict(width=1.5), boxmean=False, showlegend=False,
                             fillcolor="rgba(0,0,0,0)"))
    fig.update_yaxes(title_text=f"{VARIABLES[var]['label']} ({VARIABLES[var]['unit']})")
    style(fig, theme, 320)
    fig.update_layout(hovermode="closest")
    return fig


def corr_fig(df: pd.DataFrame, machine_id: str, theme: str) -> go.Figure:
    p = pal(theme)
    cols = ["load_pct", *VAR_KEYS]
    names = ["Carga", "Vibração", "Temperatura", "Pressão"]
    c = df[df["machine_id"] == machine_id][cols].corr().to_numpy()
    fig = go.Figure(go.Heatmap(z=c, x=names, y=names, zmin=-1, zmax=1, colorscale=[[0, p["temperature_c"]], [0.5, "#F5F7FA" if theme == "light" else "#1B2733"], [1, p["blue"]]],
                               text=[[fmt(v, 2) for v in r] for r in c], texttemplate="%{text}", xgap=2, ygap=2, hoverinfo="skip",
                               colorbar=dict(thickness=10, tickfont=dict(color=p["muted"]))))
    fig.update_yaxes(autorange="reversed")
    style(fig, theme, 320)
    fig.update_layout(hovermode=False, margin=dict(l=84, r=8, t=16, b=36))
    return fig
