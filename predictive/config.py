"""Configuração do domínio: máquinas, variáveis monitoradas e limites operacionais.

Os limites seguem a lógica de zonas de severidade usada em monitoramento de condição
(normal / atenção / crítico). Os valores numéricos são FICTÍCIOS e didáticos; em um
projeto real viriam de normas (ex.: ISO 20816 para vibração) e do fabricante.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

HISTORY_FILE = DATA_DIR / "telemetry_history.csv"
LIVE_FILE = DATA_DIR / "telemetry_live.csv"
ALERTS_FILE = DATA_DIR / "alerts.csv"
WORK_ORDERS_FILE = DATA_DIR / "work_orders.csv"
MACHINES_FILE = DATA_DIR / "machines.csv"

TICK_SECONDS = float(os.getenv("TICK_SECONDS", "2"))
HISTORY_DAYS = 14
HISTORY_STEP_MIN = 10
CONFIRM_READINGS = 3  # leituras consecutivas fora do limite para abrir um alerta

VARIABLES = {
    "vibration_mm_s": {"label": "Vibração", "unit": "mm/s", "weight": 0.5, "decimals": 2},
    "temperature_c": {"label": "Temperatura", "unit": "°C", "weight": 0.3, "decimals": 1},
    "pressure_bar": {"label": "Pressão", "unit": "bar", "weight": 0.2, "decimals": 2},
}
VAR_KEYS = list(VARIABLES)

# Limites por tipo de máquina. nominal = valor típico a 60% de carga.
# tau = constante de tempo (s) da dinâmica; meas = desvio-padrão do ruído de medição.
LIMITS = {
    "prensa": {
        "vibration_mm_s": {"nominal": 2.5, "warn_hi": 4.5, "crit_hi": 7.1, "tau": 6, "meas": 0.10, "load_k": 0.25},
        "temperature_c": {"nominal": 55.0, "warn_hi": 70.0, "crit_hi": 85.0, "tau": 240, "meas": 0.4, "load_k": 0.12},
        "pressure_bar": {"nominal": 180.0, "warn_hi": 200.0, "crit_hi": 215.0,
                         "warn_lo": 165.0, "crit_lo": 150.0, "tau": 10, "meas": 1.2, "load_k": 0.03},
    },
    "compressor": {
        "vibration_mm_s": {"nominal": 2.0, "warn_hi": 4.0, "crit_hi": 6.3, "tau": 6, "meas": 0.08, "load_k": 0.20},
        "temperature_c": {"nominal": 85.0, "warn_hi": 100.0, "crit_hi": 110.0, "tau": 300, "meas": 0.5, "load_k": 0.10},
        "pressure_bar": {"nominal": 8.0, "warn_hi": 9.0, "crit_hi": 10.0,
                         "warn_lo": 7.0, "crit_lo": 6.0, "tau": 8, "meas": 0.04, "load_k": -0.04},
    },
    "torno": {
        "vibration_mm_s": {"nominal": 1.2, "warn_hi": 2.8, "crit_hi": 4.5, "tau": 4, "meas": 0.05, "load_k": 0.30},
        "temperature_c": {"nominal": 40.0, "warn_hi": 55.0, "crit_hi": 65.0, "tau": 200, "meas": 0.3, "load_k": 0.15},
        "pressure_bar": {"nominal": 6.0, "warn_hi": 7.5, "crit_hi": 8.5,
                         "warn_lo": 4.5, "crit_lo": 3.5, "tau": 8, "meas": 0.04, "load_k": 0.02},
    },
}

TYPE_LABEL = {"prensa": "Prensa hidráulica", "compressor": "Compressor de parafuso", "torno": "Torno CNC"}
PRESSURE_LABEL = {"prensa": "Pressão hidráulica", "compressor": "Pressão de descarga", "torno": "Pressão do fluido refrigerante"}
VIB_LABEL = {"prensa": "Vibração do cilindro", "compressor": "Vibração do motor", "torno": "Vibração do spindle"}

MACHINES = [
    {"machine_id": "PR-01", "name": "Prensa Hidráulica 01", "type": "prensa", "area": "Estampagem - Linha A"},
    {"machine_id": "PR-02", "name": "Prensa Hidráulica 02", "type": "prensa", "area": "Estampagem - Linha B"},
    {"machine_id": "CP-01", "name": "Compressor de Parafuso 01", "type": "compressor", "area": "Utilidades"},
    {"machine_id": "CP-02", "name": "Compressor de Parafuso 02", "type": "compressor", "area": "Utilidades"},
    {"machine_id": "CNC-01", "name": "Torno CNC 01", "type": "torno", "area": "Usinagem"},
    {"machine_id": "CNC-02", "name": "Torno CNC 02", "type": "torno", "area": "Usinagem"},
]
MACHINE_BY_ID = {m["machine_id"]: m for m in MACHINES}
MACHINE_IDS = [m["machine_id"] for m in MACHINES]

# Desgaste (0 = novo, 1 = no limite crítico) ao fim do histórico e como evolui.
# dir = sentido do desvio (+1 acima do nominal, -1 abaixo).
WEAR_PROFILES = {
    "PR-02": {"vibration_mm_s": {"end": 0.58, "shape": "exp"},
              "temperature_c": {"end": 0.22, "shape": "linear"}},
    "CP-01": {"temperature_c": {"end": 0.52, "shape": "linear"},
              "pressure_bar": {"end": 0.30, "shape": "linear", "dir": -1}},
    "CNC-02": {"vibration_mm_s": {"end": 0.30, "shape": "linear", "spikes": True}},
}
BASE_WEAR = 0.04

# Incidentes passados no histórico: (máquina, fração do período, nº de leituras, tipo, intensidade 0..1)
INCIDENTS = [
    ("PR-01", 0.20, 5, "vazamento", 0.75),
    ("CP-02", 0.48, 8, "superaquecimento", 0.80),
    ("CNC-01", 0.66, 4, "rolamento", 1.00),
    ("PR-01", 0.80, 3, "superaquecimento", 0.60),
]

FAULTS = {
    "rolamento": {"label": "Falha de rolamento (vibração ↑)", "effects": {"vibration_mm_s": 1.15, "temperature_c": 0.25}},
    "superaquecimento": {"label": "Superaquecimento (temperatura ↑)", "effects": {"temperature_c": 1.15, "vibration_mm_s": 0.10}},
    "vazamento": {"label": "Vazamento / perda de pressão (pressão ↓)", "effects": {"pressure_bar": -1.15}},
}

STATUS_LABEL = {0: "Normal", 1: "Atenção", 2: "Crítico"}
STATUS_SHAPE = {0: "●", 1: "▲", 2: "■"}
