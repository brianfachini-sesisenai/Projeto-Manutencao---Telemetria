import numpy as np
import pandas as pd

from predictive.analytics import AlertDetector, estimate_rul, health_index, level_of, machine_status


def test_levels_two_sided_pressure():
    assert level_of("prensa", "pressure_bar", 180) == 0
    assert level_of("prensa", "pressure_bar", 160) == 1   # abaixo do limite de atenção
    assert level_of("prensa", "pressure_bar", 140) == 2   # abaixo do crítico
    assert level_of("prensa", "vibration_mm_s", 7.2) == 2


def test_health_index_monotonic():
    ok = {"vibration_mm_s": 2.5, "temperature_c": 55.0, "pressure_bar": 180.0}
    bad = {"vibration_mm_s": 7.0, "temperature_c": 80.0, "pressure_bar": 180.0}
    assert health_index("prensa", ok) > 95 > health_index("prensa", bad)
    assert machine_status("prensa", ok) == 0


def test_detector_debounce():
    det = AlertDetector(confirm=3)
    v = {"vibration_mm_s": 5.0, "temperature_c": 55.0, "pressure_bar": 180.0}
    ts = pd.Timestamp("2026-01-01")
    assert det.process("PR-01", ts, v) == [] and det.process("PR-01", ts, v) == []
    ev = det.process("PR-01", ts, v)
    assert len(ev) == 1 and ev[0]["severity"] == "Atenção"
    assert det.process("PR-01", ts, v) == []  # não repete


def test_rul_linear_trend():
    idx = pd.date_range("2026-01-01", periods=5 * 24 * 6, freq="10min")
    days = np.arange(len(idx)) / 144
    df = pd.DataFrame({"timestamp": idx, "machine_id": "PR-01", "vibration_mm_s": 2.5 + 0.3 * days,
                       "temperature_c": 55.0, "pressure_bar": 180.0})
    r = estimate_rul(df, "PR-01", "vibration_mm_s")
    expected = (7.1 - (2.5 + 0.3 * days[-1])) / 0.3
    assert abs(r["rul_days"] - expected) < 0.5 and r["r2"] > 0.99
    assert estimate_rul(df, "PR-01", "temperature_c")["rul_days"] is None
