"""학습 결과 저장 — PyQt 학습 탭과 Flask /train이 같이 쓴다.

둘이 따로 저장하면 한쪽에서 학습한 모델이 다른 쪽(Flask 모델 목록 → 시뮬 커스텀 모델)에
안 보인다. 저장 위치도 실행 위치(cwd)와 무관하게 고정한다.
"""
import datetime
import json
import os

import joblib

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# 패키징 빌드는 설치 폴더가 쓰기 불가일 수 있어 MAPS_MODELS_DIR로 쓰기 가능한 폴더를 넘긴다.
MODELS_DIR = os.environ.get("MAPS_MODELS_DIR") or os.path.join(APP_DIR, "models")

TARGET_NAMES = ["yield_stress_mpa", "uts_mpa", "elongation_pct", "area_reduction_pct"]


def metrics_by_target(r2, mae):
    return {
        name: {"r2": round(float(r2[i]), 4), "mae": round(float(mae[i]), 2)}
        for i, name in enumerate(TARGET_NAMES)
    }


def save_trained(model_engine, data_engine, model_type, samples, metrics):
    """기본 모델(material_model.pkl)을 갱신하고, 레지스트리에도 이름 붙여 보관한다.

    반환: 레지스트리 이름 (custom-<type>-<stamp>) — Flask /models 목록에 이 이름으로 뜬다.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_engine.save(os.path.join(MODELS_DIR, "material_model.pkl"))
    joblib.dump(data_engine, os.path.join(MODELS_DIR, "data_engine.pkl"))

    now = datetime.datetime.now()
    name = f"custom-{model_type}-{now:%Y%m%d_%H%M%S}"
    model_engine.save(os.path.join(MODELS_DIR, f"{name}.model.pkl"))
    joblib.dump(data_engine, os.path.join(MODELS_DIR, f"{name}.data.pkl"))
    meta = {
        "name": name,
        "model_type": model_type,
        "saved_date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "samples": int(samples),
        "metrics": metrics,
    }
    with open(os.path.join(MODELS_DIR, f"{name}.meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return name
