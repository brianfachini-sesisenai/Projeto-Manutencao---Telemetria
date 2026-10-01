"""Simulador de telemetria em tempo real + hub WebSocket + API REST de sensores.

Um thread gera uma leitura por máquina a cada TICK_SECONDS, detecta alertas, grava no CSV
e transmite o pacote a todos os clientes conectados via WebSocket (RFC 6455).
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import datetime

import numpy as np
import pandas as pd

from . import store
from .analytics import AlertDetector, health_index, level_of, machine_status
from .config import FAULTS, MACHINE_BY_ID, MACHINES, TICK_SECONDS, VAR_KEYS
from .datagen import current_wear
from .simulator_model import MachineModel, load_profile

BUFFER = 450  # leituras por máquina mantidas em memória (~15 min a 2 s)
WEAR_RATE_PER_TICK = 0.00004  # evolução lenta do desgaste durante a demonstração
FAULT_RAMP_S = 20.0


class Hub:
    """Conjunto thread-safe de conexões WebSocket."""

    def __init__(self):
        self._clients: set = set()
        self._lock = threading.Lock()

    def add(self, ws):
        with self._lock:
            self._clients.add(ws)

    def remove(self, ws):
        with self._lock:
            self._clients.discard(ws)

    def count(self) -> int:
        return len(self._clients)

    def broadcast(self, text: str) -> int:
        with self._lock:
            clients = list(self._clients)
        sent = 0
        for ws in clients:
            try:
                ws.send(text)
                sent += 1
            except Exception:
                self.remove(ws)
        return sent


class Simulator(threading.Thread):
    def __init__(self, hub: Hub, seed: int = 7):
        super().__init__(daemon=True, name="telemetry-simulator")
        self.hub = hub
        self.rng = np.random.default_rng(seed)
        self.models = {m["machine_id"]: MachineModel(m["machine_id"], self.rng) for m in MACHINES}
        self.wear = {m["machine_id"]: current_wear(m["machine_id"]) for m in MACHINES}
        self.buffers = {m["machine_id"]: deque(maxlen=BUFFER) for m in MACHINES}
        self.fault_target: dict[str, dict[str, float]] = {m["machine_id"]: {} for m in MACHINES}
        self.detector = AlertDetector()
        self.last_payload_bytes = 0
        self.ticks = 0
        self.recent_alerts: deque = deque(maxlen=8)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._warm_up()

    # ---------- controle de cenários ----------
    def inject_fault(self, machine_id: str, kind: str) -> None:
        if machine_id in self.fault_target and kind in FAULTS:
            self.fault_target[machine_id][kind] = 1.0

    def clear_faults(self, machine_id: str | None = None) -> None:
        for mid in ([machine_id] if machine_id else list(self.fault_target)):
            for kind in list(self.fault_target[mid]):
                self.fault_target[mid][kind] = 0.0

    def active_faults(self) -> dict[str, list[str]]:
        out = {}
        for mid, kinds in self.fault_target.items():
            act = [k for k, t in kinds.items() if t > 0 or self.models[mid].fault_level.get(k, 0) > 0.02]
            if act:
                out[mid] = act
        return out

    # ---------- ciclo ----------
    def _warm_up(self) -> None:
        """Preenche o buffer com ~2 min de leituras para os gráficos já nascerem preenchidos."""
        now = datetime.now()
        n = 60
        for i in range(n):
            ts = now - pd.Timedelta(seconds=(n - i) * TICK_SECONDS)
            for mid, model in self.models.items():
                vals = model.step(TICK_SECONDS, load_profile(ts, self.rng), self.wear[mid])
                self.buffers[mid].append(self._reading(mid, ts, vals))
        # Condições que já existiam ao iniciar não geram alerta novo (já constam no CSV).
        for mid, buf in self.buffers.items():
            mtype = MACHINE_BY_ID[mid]["type"]
            for var in VAR_KEYS:
                self.detector.active[(mid, var)] = level_of(mtype, var, buf[-1][var])

    def _reading(self, mid: str, ts, vals: dict) -> dict:
        mtype = MACHINE_BY_ID[mid]["type"]
        r = {"timestamp": pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S"), "machine_id": mid}
        r.update({v: round(float(vals[v]), 3) for v in VAR_KEYS})
        r["load_pct"] = round(float(vals["load_pct"]), 1)
        r["status"] = machine_status(mtype, r)
        r["health_index"] = health_index(mtype, r)
        return r

    def _update_faults(self, dt: float) -> None:
        for mid, model in self.models.items():
            for kind, target in self.fault_target[mid].items():
                cur = model.fault_level.get(kind, 0.0)
                step = dt / FAULT_RAMP_S
                cur = min(target, cur + step) if cur < target else max(target, cur - step)
                model.fault_level[kind] = cur
                if cur <= 0 and target <= 0:
                    model.fault_level.pop(kind, None)
                    self.fault_target[mid].pop(kind, None)

    def tick(self) -> dict:
        ts = datetime.now()
        self._update_faults(TICK_SECONDS)
        rows, events = [], []
        for mid, model in self.models.items():
            for var in self.wear[mid]:
                self.wear[mid][var] = min(0.98, self.wear[mid][var] + WEAR_RATE_PER_TICK * (1 if self.wear[mid][var] > 0.1 else 0.1))
            impulse = mid == "CNC-02" and self.rng.random() < 0.004
            vals = model.step(TICK_SECONDS, load_profile(ts, self.rng), self.wear[mid], impulse)
            r = self._reading(mid, ts, vals)
            rows.append(r)
            events += self.detector.process(mid, ts, r)
        with self._lock:
            for r in rows:
                self.buffers[r["machine_id"]].append(r)
            self.ticks += 1
        store.append_live([{k: r[k] for k in ("timestamp", "machine_id", *VAR_KEYS, "load_pct")} for r in rows])
        new_alerts = store.append_alerts(events)
        for a in new_alerts:
            self.recent_alerts.appendleft(a)
        payload = {"type": "tick", "ts": rows[0]["timestamp"], "readings": rows,
                   "alerts": new_alerts, "faults": self.active_faults()}
        text = json.dumps(payload, ensure_ascii=False)
        self.last_payload_bytes = len(text.encode())
        self.hub.broadcast(text)
        return payload

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "machines": {
                    mid: {
                        "t": [r["timestamp"] for r in buf],
                        "vib": [r["vibration_mm_s"] for r in buf],
                        "temp": [r["temperature_c"] for r in buf],
                        "press": [r["pressure_bar"] for r in buf],
                        "load": [r["load_pct"] for r in buf],
                        "status": buf[-1]["status"] if buf else 0,
                        "hi": buf[-1]["health_index"] if buf else 100,
                    } for mid, buf in self.buffers.items()
                },
                "alerts": list(self.recent_alerts),
                "faults": self.active_faults(),
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    def latest(self) -> list[dict]:
        with self._lock:
            return [buf[-1] for buf in self.buffers.values() if buf]

    def run(self) -> None:
        next_t = time.monotonic()
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # o simulador nunca deve derrubar o app
                print("[simulator] erro no tick:", exc)
            next_t += TICK_SECONDS
            time.sleep(max(0.0, next_t - time.monotonic()))

    def stop(self) -> None:
        self._stop.set()


def register_routes(server, sim: Simulator, hub: Hub) -> None:
    """Registra WebSocket (/ws) e API REST (/api/*) no servidor Flask do Dash."""
    from flask import jsonify, request
    from flask_sock import Sock

    sock = Sock(server)

    @sock.route("/ws")
    def ws_route(ws):
        hub.add(ws)
        try:
            while True:
                if ws.receive() is None:
                    break
        except Exception:
            pass
        finally:
            hub.remove(ws)

    @server.get("/api/sensors")
    def api_sensors():
        return jsonify({"tick_seconds": TICK_SECONDS, "readings": sim.latest()})

    @server.get("/api/snapshot")
    def api_snapshot():
        return jsonify(sim.snapshot())

    @server.get("/api/history")
    def api_history():
        machine = request.args.get("machine")
        df = store.load_history()
        if machine:
            df = df[df["machine_id"] == machine]
        limit = min(int(request.args.get("limit", 500)), 5000)
        df = df.tail(limit).assign(timestamp=lambda d: d["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"))
        return jsonify(df.to_dict("records"))

    @server.get("/api/health")
    def api_health():
        return jsonify({"status": "ok", "ws_clients": hub.count(), "ticks": sim.ticks})
