"""Camada de persistência em CSV (o 'banco de dados' do protótipo).

Escritas são serializadas por um lock de processo. Leituras do histórico são cacheadas e
recarregadas apenas quando o arquivo muda (mtime).
"""
from __future__ import annotations

import csv
import threading
from datetime import datetime

import pandas as pd

from .config import ALERTS_FILE, HISTORY_FILE, LIVE_FILE, VAR_KEYS, WORK_ORDERS_FILE
from .datagen import ALERT_COLUMNS, WO_COLUMNS

_lock = threading.RLock()
_history_cache: dict = {"mtime": None, "df": None}


def load_history() -> pd.DataFrame:
    with _lock:
        mtime = HISTORY_FILE.stat().st_mtime
        if _history_cache["mtime"] != mtime:
            _history_cache["df"] = pd.read_csv(HISTORY_FILE, parse_dates=["timestamp"])
            _history_cache["mtime"] = mtime
        return _history_cache["df"]


# ---------- telemetria ao vivo (apêndice) ----------
def reset_live_file() -> None:
    with _lock, open(LIVE_FILE, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "machine_id", *VAR_KEYS, "load_pct"])


def append_live(rows: list[dict]) -> None:
    with _lock, open(LIVE_FILE, "a", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow([r["timestamp"], r["machine_id"], *[r[v] for v in VAR_KEYS], r["load_pct"]])


# ---------- alertas ----------
def _read(path, columns) -> pd.DataFrame:
    with _lock:
        if not path.exists():
            return pd.DataFrame(columns=columns)
        return pd.read_csv(path, dtype=str, keep_default_na=False)


def _write(path, df: pd.DataFrame) -> None:
    with _lock:
        df.to_csv(path, index=False)


def list_alerts() -> pd.DataFrame:
    df = _read(ALERTS_FILE, ALERT_COLUMNS)
    return df.sort_values("timestamp", ascending=False).reset_index(drop=True)


def append_alerts(events: list[dict]) -> list[dict]:
    """Grava alertas novos (atribuindo ids) e devolve as linhas completas."""
    if not events:
        return []
    with _lock:
        df = _read(ALERTS_FILE, ALERT_COLUMNS)
        n = len(df)
        full = []
        for e in events:
            n += 1
            row = {c: "" for c in ALERT_COLUMNS}
            row.update(e)
            row.update(alert_id=f"AL-{n:05d}", status="Aberto")
            full.append(row)
        _write(ALERTS_FILE, pd.concat([df, pd.DataFrame(full)], ignore_index=True))
        return full


def set_alert_status(alert_ids: list[str], status: str, user: str = "Engenharia de Manutenção") -> int:
    with _lock:
        df = _read(ALERTS_FILE, ALERT_COLUMNS)
        mask = df["alert_id"].isin(alert_ids)
        df.loc[mask, "status"] = status
        if status == "Reconhecido":
            df.loc[mask, "acknowledged_by"] = user
        _write(ALERTS_FILE, df)
        return int(mask.sum())


# ---------- ordens de serviço ----------
def list_work_orders() -> pd.DataFrame:
    df = _read(WORK_ORDERS_FILE, WO_COLUMNS)
    return df.sort_values("created_at", ascending=False).reset_index(drop=True)


def create_work_order(machine_id: str, priority: str, wo_type: str, description: str,
                      alert_id: str = "", assigned_to: str = "A definir", due_days: int = 3) -> dict:
    with _lock:
        df = _read(WORK_ORDERS_FILE, WO_COLUMNS)
        now = datetime.now()
        row = {
            "wo_id": f"OS-{len(df) + 1:04d}",
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "machine_id": machine_id, "alert_id": alert_id, "priority": priority, "type": wo_type,
            "description": description, "status": "Aberta", "assigned_to": assigned_to,
            "due_date": (now + pd.Timedelta(days=due_days)).strftime("%Y-%m-%d %H:%M:%S"),
        }
        _write(WORK_ORDERS_FILE, pd.concat([df, pd.DataFrame([row])], ignore_index=True))
        if alert_id:
            al = _read(ALERTS_FILE, ALERT_COLUMNS)
            al.loc[al["alert_id"] == alert_id, "work_order_id"] = row["wo_id"]
            _write(ALERTS_FILE, al)
        return row


def set_work_order_status(wo_ids: list[str], status: str) -> int:
    with _lock:
        df = _read(WORK_ORDERS_FILE, WO_COLUMNS)
        mask = df["wo_id"].isin(wo_ids)
        df.loc[mask, "status"] = status
        _write(WORK_ORDERS_FILE, df)
        return int(mask.sum())
