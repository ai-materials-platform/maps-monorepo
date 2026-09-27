"""STRESS-STRAIN 상세 탐색기 크래시 재현 (offscreen)."""
import faulthandler
import os
import sys
import traceback

faulthandler.enable()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, "apps/prediction")

import joblib
import numpy as np

from src.engine.model_engine import ModelEngine

print("loading engines...", flush=True)
data_engine = joblib.load("apps/prediction/models/pretrained_data_engine.pkl")
data_engine.file_path = None
model_engine = ModelEngine(model_type="RF", output_dim=4)
model_engine.load("apps/prediction/models/pretrained_material_model.pkl")

cols = list(data_engine.get_selected_training_columns())
print("n cols:", len(cols), flush=True)

base = {c: 0.0 for c in cols}
realistic = {
    "Fe": 70.0, "C": 0.05, "Si": 0.4, "Mn": 1.5, "P": 0.01, "S": 0.005,
    "Ni": 8.0, "Cr": 18.0, "Mo": 2.0, "Cu": 0.1, "V": 0.05, "N": 0.02,
    "Nb": 0.01, "Ti": 0.01, "B": 0.001, "Al": 0.03,
    "Solution_treatment_temperature": 1323.0,
    "Solution_treatment_time(s)": 3600.0,
    "Grains mm-2": 12000.0,
    "Temperature (K)": 293.0,
}
for k, v in realistic.items():
    if k in base:
        base[k] = v

print("running inference...", flush=True)
scaled = data_engine.get_inference_data(base)
mean_scaled, _std = model_engine.predict(scaled)
mean = np.asarray(data_engine.scaler_y.inverse_transform(mean_scaled))[0]
print("mean:", mean, flush=True)


def safe_float(x, default=0.0):
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def estimate_modulus(t_k):
    t = safe_float(t_k, 293.0)
    return 200000.0 * (1.0 - 0.0004 * max(t - 293.0, 0.0))


def build_fn(mean_vec, input_dict):
    from src.gui.mixins.charts_mixin import ChartsMixin

    class Stub:
        def _safe_float(self, value, default=0.0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return float(default)

        def _estimate_elastic_modulus(self, temperature_k):
            temperature_k = self._safe_float(temperature_k, 293.15)
            temperature_c = temperature_k - 273.15
            softening_factor = 1.0 - max(0.0, temperature_c - 20.0) * 0.00022
            return float(np.clip(193000.0 * softening_factor, 125000.0, 210000.0))

    return ChartsMixin._build_stress_strain_profile(Stub(), mean_vec, input_dict)


print("creating QApplication...", flush=True)
from PyQt6.QtWidgets import QApplication

app = QApplication([])
print("creating dialog...", flush=True)
from src.gui.widgets.strain_explore_dialog import StrainExploreDialog

try:
    dlg = StrainExploreDialog(model_engine, data_engine, base, build_fn, None)
    dlg.show()
    app.processEvents()
    print("DIALOG OK", flush=True)
except Exception:
    traceback.print_exc()
    print("DIALOG FAILED", flush=True)
