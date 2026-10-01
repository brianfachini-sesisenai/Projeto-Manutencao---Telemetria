"""Geração do histórico fictício (CSV) com degradação progressiva em algumas máquinas."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analytics import AlertDetector
from .config import (ALERTS_FILE, BASE_WEAR, DATA_DIR, HISTORY_DAYS, HISTORY_FILE, HISTORY_STEP_MIN,
                     INCIDENTS, MACHINES, MACHINES_FILE, WEAR_PROFILES, WORK_ORDERS_FILE)
from .simulator_model import MachineModel, load_profile

ALERT_COLUMNS = ["alert_id", "timestamp", "machine_id", "variable", "severity", "value", "limit",
                 "status", "message", "acknowledged_by", "work_order_id"]
WO_COLUMNS = ["wo_id", "created_at", "machine_id", "alert_id", "priority", "type", "description",
              "status", "assigned_to", "due_date"]


def wear_at(machine_id: str, var: str, frac: float, rng_walk: float = 0.0) -> float:
    """Desgaste na fração `frac` (0..1) do período histórico."""
    prof = WEAR_PROFILES.get(machine_id, {}).get(var)
    if not prof:
        return BASE_WEAR + rng_walk
    end = prof["end"]
    if prof["shape"] == "exp":
        k = 4.0
        shape = (np.exp(k * frac) - 1) / (np.exp(k) - 1)
    else:
        shape = frac
    return BASE_WEAR + (end - BASE_WEAR) * shape + rng_walk


def current_wear(machine_id: str) -> dict[str, float]:
    return {v: wear_at(machine_id, v, 1.0) for v in ("vibration_mm_s", "temperature_c", "pressure_bar")}


def generate(end: pd.Timestamp | None = None, seed: int = 42) -> pd.DataFrame:
    end = (end or pd.Timestamp.now()).floor(f"{HISTORY_STEP_MIN}min")
    idx = pd.date_range(end=end, periods=HISTORY_DAYS * 24 * 60 // HISTORY_STEP_MIN, freq=f"{HISTORY_STEP_MIN}min")
    rows = []
    for i, m in enumerate(MACHINES):
        rng = np.random.default_rng(seed + i)
        model = MachineModel(m["machine_id"], rng)
        walk = {v: 0.0 for v in ("vibration_mm_s", "temperature_c", "pressure_bar")}
        spikes = WEAR_PROFILES.get(m["machine_id"], {}).get("vibration_mm_s", {}).get("spikes", False)
        for n, ts in enumerate(idx):
            frac = n / (len(idx) - 1)
            for v in walk:
                walk[v] = float(np.clip(walk[v] * 0.995 + rng.normal(0, 0.004), -0.03, 0.05))
            wear = {v: wear_at(m["machine_id"], v, frac, walk[v]) for v in walk}
            model.fault_level = {}
            for inc_m, inc_frac, inc_len, inc_kind, inc_level in INCIDENTS:
                start = int(inc_frac * len(idx))
                if inc_m == m["machine_id"] and start <= n < start + inc_len:
                    model.fault_level[inc_kind] = inc_level
            impulse = bool(spikes and frac > 0.4 and rng.random() < 0.012)
            r = model.step(HISTORY_STEP_MIN * 60, load_profile(ts, rng), wear, impulse)
            rows.append({"timestamp": ts, "machine_id": m["machine_id"], **r})
    df = pd.DataFrame(rows)
    for c in ("vibration_mm_s", "temperature_c", "pressure_bar", "load_pct"):
        df[c] = df[c].round(3)
    return df


def _seed_alerts(df: pd.DataFrame) -> pd.DataFrame:
    det = AlertDetector()
    events = []
    for rec in df.sort_values("timestamp").itertuples(index=False):
        events += det.process(rec.machine_id, rec.timestamp, rec._asdict())
    al = pd.DataFrame(events, columns=["timestamp", "machine_id", "variable", "severity", "value", "limit", "message"])
    if al.empty:
        return pd.DataFrame(columns=ALERT_COLUMNS)
    cutoff = pd.Timestamp(df["timestamp"].max()) - pd.Timedelta(hours=36)
    al["status"] = np.where(pd.to_datetime(al["timestamp"]) >= cutoff, "Aberto", "Resolvido")
    al["acknowledged_by"] = ""
    al["work_order_id"] = ""
    al.insert(0, "alert_id", [f"AL-{i + 1:05d}" for i in range(len(al))])
    return al[ALERT_COLUMNS]


def _seed_work_orders(df: pd.DataFrame) -> pd.DataFrame:
    end = pd.Timestamp(df["timestamp"].max())
    rows = [
        ("OS-0001", end - pd.Timedelta(days=9), "PR-01", "", "Média", "Preventiva", "Troca de óleo hidráulico e filtro", "Concluída", "Equipe Mecânica A", end - pd.Timedelta(days=8)),
        ("OS-0002", end - pd.Timedelta(days=6), "CP-02", "", "Baixa", "Preventiva", "Limpeza do resfriador e verificação de correia", "Concluída", "Equipe Utilidades", end - pd.Timedelta(days=5)),
        ("OS-0003", end - pd.Timedelta(days=2), "PR-02", "", "Alta", "Preditiva", "Inspeção de rolamentos do cilindro principal (tendência de vibração)", "Em andamento", "Equipe Mecânica B", end + pd.Timedelta(days=1)),
        ("OS-0004", end - pd.Timedelta(days=1), "CP-01", "", "Média", "Preditiva", "Verificar eficiência do resfriador (temperatura em alta)", "Aberta", "Equipe Utilidades", end + pd.Timedelta(days=3)),
    ]
    out = pd.DataFrame(rows, columns=["wo_id", "created_at", "machine_id", "alert_id", "priority", "type", "description", "status", "assigned_to", "due_date"])
    for c in ("created_at", "due_date"):
        out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out[WO_COLUMNS]


def build_all(seed: int = 42) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate(seed=seed)
    df.to_csv(HISTORY_FILE, index=False, date_format="%Y-%m-%d %H:%M:%S")
    pd.DataFrame(MACHINES).to_csv(MACHINES_FILE, index=False)
    _seed_alerts(df).to_csv(ALERTS_FILE, index=False)
    _seed_work_orders(df).to_csv(WORK_ORDERS_FILE, index=False)


def ensure_data(max_age_hours: float = 12) -> bool:
    """Gera os CSVs se não existirem ou se o histórico estiver velho demais. Retorna True se regenerou."""
    files = (HISTORY_FILE, ALERTS_FILE, WORK_ORDERS_FILE, MACHINES_FILE)
    stale = True
    if all(f.exists() for f in files):
        last = pd.read_csv(HISTORY_FILE, usecols=["timestamp"], parse_dates=["timestamp"])["timestamp"].max()
        stale = (pd.Timestamp.now() - last) > pd.Timedelta(hours=max_age_hours)
    if stale:
        build_all()
    return stale


if __name__ == "__main__":
    build_all()
    print("Dados gerados em", DATA_DIR)
