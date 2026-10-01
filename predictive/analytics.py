"""Análises de condição: severidade, índice de saúde, anomalias, RUL e detector de alertas."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CONFIRM_READINGS, LIMITS, MACHINE_BY_ID, STATUS_LABEL, VAR_KEYS, VARIABLES


def _lim(mtype: str, var: str) -> dict:
    return LIMITS[mtype][var]


def level_of(mtype: str, var: str, value: float) -> int:
    """0 = normal, 1 = atenção, 2 = crítico."""
    lim = _lim(mtype, var)
    if value >= lim["crit_hi"] or value <= lim.get("crit_lo", -np.inf):
        return 2
    if value >= lim["warn_hi"] or value <= lim.get("warn_lo", -np.inf):
        return 1
    return 0


def exceed_score(mtype: str, var: str, value: float) -> float:
    """Fração do caminho nominal -> limite crítico (0 = nominal, 1 = no limite crítico)."""
    lim = _lim(mtype, var)
    if value >= lim["nominal"]:
        return max(0.0, (value - lim["nominal"]) / (lim["crit_hi"] - lim["nominal"]))
    if "crit_lo" in lim:
        return max(0.0, (lim["nominal"] - value) / (lim["nominal"] - lim["crit_lo"]))
    return 0.0


def health_index(mtype: str, values: dict[str, float]) -> float:
    """Índice de saúde 0-100: combina o pior desvio (50%) e a média ponderada (50%)."""
    scores = {v: min(exceed_score(mtype, v, values[v]), 1.0) for v in VAR_KEYS}
    worst = max(scores.values())
    weighted = sum(VARIABLES[v]["weight"] * scores[v] for v in VAR_KEYS)
    return float(round(100 * (1 - min(1.0, 0.5 * worst + 0.5 * weighted)), 1))


def machine_status(mtype: str, values: dict[str, float]) -> int:
    return max(level_of(mtype, v, values[v]) for v in VAR_KEYS)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Versão vetorizada: adiciona colunas s_<var>, level_<var>, status e health_index."""
    out = df.copy()
    types = out["machine_id"].map(lambda m: MACHINE_BY_ID[m]["type"])
    score_cols = {}
    for var in VAR_KEYS:
        col = out[var].to_numpy(float)
        nominal = types.map(lambda t: LIMITS[t][var]["nominal"]).to_numpy(float)
        crit_hi = types.map(lambda t: LIMITS[t][var]["crit_hi"]).to_numpy(float)
        warn_hi = types.map(lambda t: LIMITS[t][var]["warn_hi"]).to_numpy(float)
        crit_lo = types.map(lambda t: LIMITS[t][var].get("crit_lo", np.nan)).to_numpy(float)
        warn_lo = types.map(lambda t: LIMITS[t][var].get("warn_lo", np.nan)).to_numpy(float)
        up = np.clip((col - nominal) / (crit_hi - nominal), 0, None)
        down = np.where(np.isnan(crit_lo), 0, np.clip((nominal - col) / (nominal - crit_lo), 0, None))
        score = np.where(col >= nominal, up, down)
        crit = (col >= crit_hi) | (~np.isnan(crit_lo) & (col <= crit_lo))
        warn = (col >= warn_hi) | (~np.isnan(warn_lo) & (col <= warn_lo))
        out[f"s_{var}"] = score
        out[f"level_{var}"] = np.where(crit, 2, np.where(warn, 1, 0))
        score_cols[var] = np.clip(score, 0, 1)
    worst = np.max(np.vstack([score_cols[v] for v in VAR_KEYS]), axis=0)
    weighted = sum(VARIABLES[v]["weight"] * score_cols[v] for v in VAR_KEYS)
    out["health_index"] = np.round(100 * (1 - np.clip(0.5 * worst + 0.5 * weighted, 0, 1)), 1)
    out["status"] = np.max(np.vstack([out[f"level_{v}"] for v in VAR_KEYS]), axis=0)
    return out


def rolling_anomalies(series: pd.Series, window: int = 72, threshold: float = 3.5) -> pd.DataFrame:
    """Z-score robusto (mediana/MAD) em janela móvel. Marca desvios de curto prazo."""
    med = series.rolling(window, min_periods=window // 3).median()
    mad = (series - med).abs().rolling(window, min_periods=window // 3).median()
    z = 0.6745 * (series - med) / mad.replace(0, np.nan)
    return pd.DataFrame({"z": z, "anomaly": z.abs() > threshold})


def estimate_rul(df: pd.DataFrame, machine_id: str, var: str, days: int = 5) -> dict:
    """Regressão linear sobre médias horárias dos últimos `days` dias, extrapolada até o limite crítico.

    Modelo didático: assume tendência aproximadamente linear. Retorna dias restantes,
    inclinação (unidade/dia) e R² como indicador de confiança do ajuste.
    """
    mtype = MACHINE_BY_ID[machine_id]["type"]
    lim = _lim(mtype, var)
    d = df[df["machine_id"] == machine_id].set_index("timestamp")[var].sort_index()
    d = d[d.index >= d.index.max() - pd.Timedelta(days=days)].resample("1h").mean().dropna()
    result = {"var": var, "rul_days": None, "slope_per_day": 0.0, "r2": 0.0, "target": None, "fit": None}
    if len(d) < 12:
        return result
    t = (d.index - d.index[0]).total_seconds().to_numpy() / 86400.0
    y = d.to_numpy(float)
    slope, intercept = np.polyfit(t, y, 1)
    pred = slope * t + intercept
    ss_res, ss_tot = float(((y - pred) ** 2).sum()), float(((y - y.mean()) ** 2).sum())
    r2 = 0.0 if ss_tot == 0 else max(0.0, 1 - ss_res / ss_tot)
    current = slope * t[-1] + intercept
    result.update(slope_per_day=float(slope), r2=float(r2), fit=(d.index[0], slope, intercept))
    min_slope = 0.004 * abs(lim["crit_hi"] - lim["nominal"])  # ignora tendência desprezível
    if slope > min_slope:
        target = lim["crit_hi"]
    elif slope < -min_slope and "crit_lo" in lim:
        target = lim["crit_lo"]
    else:
        return result
    result["target"] = target
    remaining = (target - current) / slope
    result["rul_days"] = float(max(0.0, remaining))
    return result


class AlertDetector:
    """Abre alerta quando o nível piora por N leituras consecutivas (debounce contra ruído)."""

    def __init__(self, confirm: int = CONFIRM_READINGS, release: int = 8):
        self.confirm, self.release = confirm, release
        self.active: dict[tuple[str, str], int] = {}
        self._rise: dict[tuple[str, str], tuple[int, int]] = {}
        self._fall: dict[tuple[str, str], int] = {}

    def process(self, machine_id: str, ts, values: dict[str, float]) -> list[dict]:
        mtype = MACHINE_BY_ID[machine_id]["type"]
        events = []
        for var in VAR_KEYS:
            key, val = (machine_id, var), values[var]
            level = level_of(mtype, var, val)
            current = self.active.get(key, 0)
            if level > current:
                cand, n = self._rise.get(key, (level, 0))
                n = n + 1 if cand == level else 1
                self._rise[key] = (level, n)
                self._fall.pop(key, None)
                if n >= self.confirm:
                    self.active[key] = level
                    self._rise.pop(key, None)
                    events.append(_alert_row(machine_id, mtype, var, level, val, ts))
            elif level < current:
                self._rise.pop(key, None)
                self._fall[key] = self._fall.get(key, 0) + 1
                if self._fall[key] >= self.release:
                    self.active[key] = level
                    self._fall.pop(key, None)
            else:
                self._rise.pop(key, None)
                self._fall.pop(key, None)
        return events


def _alert_row(machine_id: str, mtype: str, var: str, level: int, value: float, ts) -> dict:
    lim = _lim(mtype, var)
    low_side = value < lim["nominal"]
    key = ("crit" if level == 2 else "warn") + ("_lo" if low_side else "_hi")
    limit = lim[key]
    info = VARIABLES[var]
    sentido = "abaixo" if low_side else "acima"
    nome = "limite crítico" if level == 2 else "limite de atenção"
    msg = f"{info['label']} {sentido} do {nome}: {value:.{info['decimals']}f} {info['unit']} (limite {limit:g} {info['unit']})".replace(".", ",")
    return {
        "timestamp": pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": machine_id,
        "variable": var,
        "severity": STATUS_LABEL[level],
        "value": round(float(value), 3),
        "limit": limit,
        "message": msg,
    }
