"""Modelo físico-estatístico simplificado das máquinas (compartilhado por histórico e streaming)."""
from __future__ import annotations

import math

import numpy as np

from .config import FAULTS, LIMITS, MACHINE_BY_ID, VAR_KEYS, WEAR_PROFILES


def load_profile(ts, rng: np.random.Generator | None = None) -> float:
    """Carga (%) ao longo do dia: dois turnos de produção, madrugada ociosa."""
    h = ts.hour + ts.minute / 60 + ts.second / 3600
    on = 0.5 * (1 + math.tanh((h - 6) / 1.5)) * 0.5 * (1 + math.tanh((22 - h) / 1.5))
    base = 30 + 52 * on
    if ts.weekday() >= 5:
        base *= 0.6
    return base + (rng.normal(0, 2.0) if rng is not None else 0.0)


class MachineModel:
    """Estado dinâmico de uma máquina: cada variável segue o alvo com constante de tempo `tau`."""

    def __init__(self, machine_id: str, rng: np.random.Generator):
        self.id = machine_id
        self.mtype = MACHINE_BY_ID[machine_id]["type"]
        self.rng = rng
        self.state: dict[str, float | None] = {v: None for v in VAR_KEYS}
        self.fault_level: dict[str, float] = {}  # kind -> nível atual 0..1

    def wear_effect(self, var: str, wear: dict[str, float]) -> float:
        lim = LIMITS[self.mtype][var]
        profile = WEAR_PROFILES.get(self.id, {}).get(var, {})
        direction = profile.get("dir", 1)
        w = wear.get(var, 0.0)
        span = (lim["crit_hi"] - lim["nominal"]) if direction > 0 else (lim["nominal"] - lim["crit_lo"])
        return direction * w * span

    def fault_effect(self, var: str) -> float:
        lim = LIMITS[self.mtype][var]
        total = 0.0
        for kind, level in self.fault_level.items():
            eff = FAULTS[kind]["effects"].get(var)
            if eff and level > 0:
                span = (lim["crit_hi"] - lim["nominal"]) if eff > 0 else (lim["nominal"] - lim["crit_lo"])
                total += eff * level * span
        return total

    def step(self, dt_s: float, load: float, wear: dict[str, float], impulse: bool = False) -> dict[str, float]:
        out = {}
        for var in VAR_KEYS:
            lim = LIMITS[self.mtype][var]
            target = lim["nominal"] * (1 + lim["load_k"] * (load - 60) / 100)
            target += self.wear_effect(var, wear) + self.fault_effect(var)
            if var == "vibration_mm_s" and impulse:
                target += 0.8 * (lim["crit_hi"] - lim["nominal"])
            cur = self.state[var]
            if cur is None:
                cur = target
            alpha = 1 - math.exp(-dt_s / lim["tau"])
            cur = cur + alpha * (target - cur)
            self.state[var] = cur
            out[var] = cur + self.rng.normal(0, lim["meas"])
        out["load_pct"] = float(np.clip(load, 0, 100))
        return out
