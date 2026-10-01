"""Interpretações em linguagem natural: o 'porquê' de cada estado e a tendência prevista."""
from __future__ import annotations

import pandas as pd

from . import store
from .analytics import estimate_rul, exceed_score, level_of
from .config import HISTORY_FILE, LIMITS, MACHINE_BY_ID, MACHINE_IDS, PRESSURE_LABEL, VAR_KEYS, VARIABLES
from .figs import fmt

_cache: dict = {"mtime": None, "value": None}
SHORT = {"vibration_mm_s": "vib", "temperature_c": "temp", "pressure_bar": "press"}


def label(machine_id: str, var: str) -> str:
    if var == "pressure_bar":
        return PRESSURE_LABEL[MACHINE_BY_ID[machine_id]["type"]]
    return VARIABLES[var]["label"]


def fleet_trends() -> dict:
    """RUL por máquina/variável, calculado a partir do histórico (cache por mtime do CSV)."""
    mtime = HISTORY_FILE.stat().st_mtime
    if _cache["mtime"] != mtime:
        df = store.load_history()
        out = {}
        for mid in MACHINE_IDS:
            ruls = {v: estimate_rul(df, mid, v, days=5) for v in VAR_KEYS}
            finite = [r for r in ruls.values() if r["rul_days"] is not None and r["rul_days"] <= 60]
            out[mid] = {"ruls": ruls, "main": min(finite, key=lambda r: r["rul_days"]) if finite else None}
        _cache.update(mtime=mtime, value=out)
    return _cache["value"]


def confidence(r2: float) -> str:
    return "alta" if r2 >= 0.8 else "média" if r2 >= 0.5 else "baixa"


def reason(machine_id: str, last: dict) -> str:
    """Frase que explica por que a máquina está nesse estado (variável mais crítica agora)."""
    mtype = MACHINE_BY_ID[machine_id]["type"]
    var = max(VAR_KEYS, key=lambda v: (level_of(mtype, v, last[v]), exceed_score(mtype, v, last[v])))
    lvl = level_of(mtype, var, last[var])
    info, lim = VARIABLES[var], LIMITS[mtype][var]
    if lvl == 0:
        return "Todas as variáveis dentro da faixa normal."
    low = last[var] < lim["nominal"]
    key = ("crit" if lvl == 2 else "warn") + ("_lo" if low else "_hi")
    nome = "crítico" if lvl == 2 else "de atenção"
    d = info["decimals"]
    if round(last[var], d) == round(lim[key], d):  # evita "100,0 acima de 100,0"
        d += 1
    return (f"{label(machine_id, var)} em {fmt(last[var], d)} {info['unit']} — "
            f"{'abaixo' if low else 'acima'} do limite {nome} ({fmt(lim[key], info['decimals'])} {info['unit']}).")


def trend_text(machine_id: str) -> str | None:
    main = fleet_trends()[machine_id]["main"]
    if not main:
        return None
    unit = VARIABLES[main["var"]]["unit"]
    verb = "subindo" if main["slope_per_day"] > 0 else "caindo"
    return (f"{label(machine_id, main['var'])} {verb} {fmt(abs(main['slope_per_day']), 2)} {unit}/dia; "
            f"limite crítico em ≈ {fmt(main['rul_days'], 0)} dias.")


def recommendation(days: float | None) -> str:
    if days is None:
        return "Manter o plano de manutenção atual."
    if days < 7:
        return "Agendar inspeção ainda esta semana."
    if days < 21:
        return "Incluir na próxima parada programada."
    return "Acompanhar a evolução nas próximas semanas."


def ago(ts: str) -> str:
    secs = (pd.Timestamp.now() - pd.Timestamp(ts)).total_seconds()
    if secs < 90:
        return "agora há pouco"
    if secs < 3600:
        return f"há {int(secs // 60)} min"
    if secs < 86400:
        return f"há {int(secs // 3600)} h"
    return f"há {int(secs // 86400)} d"
