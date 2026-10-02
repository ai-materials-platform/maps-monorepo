import os
import datetime
import json
import sys

# 실행 위치와 무관하게 apps/prediction을 import 경로에 포함
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from src.engine.data_engine import DataEngine
from src.engine.model_engine import ModelEngine
from src.engine.high_carbon_correction import (
    apply_high_carbon_correction,
    correction_badge,
)

TARGET_NAMES = ['yield_stress_mpa', 'uts_mpa', 'elongation_pct', 'area_reduction_pct']

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'data/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

data_engine = DataEngine(None)
model_engine = None

# 사전학습 번들 (GUI 사전학습 탭과 동일 파일)
pretrained_model_engine = None
pretrained_data_engine = None
pretrained_meta = {}


def _load_saved_resources():
    global data_engine, model_engine
    engine_path = 'models/data_engine.pkl'
    model_path = 'models/material_model.pkl'
    if os.path.exists(engine_path):
        data_engine = joblib.load(engine_path)
    if os.path.exists(model_path):
        model_engine = ModelEngine(model_type='RF', output_dim=4)
        model_engine.load(model_path)


def _load_pretrained_bundle():
    """사전학습 번들을 로드한다. 없으면 (False, 이유) 반환."""
    global pretrained_model_engine, pretrained_data_engine, pretrained_meta
    if pretrained_model_engine is not None and pretrained_data_engine is not None:
        return True, ""
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'models'))
    model_path = os.path.join(models_dir, 'pretrained_material_model.pkl')
    data_engine_path = os.path.join(models_dir, 'pretrained_data_engine.pkl')
    meta_path = os.path.join(models_dir, 'pretrained_material_model_meta.json')
    missing = [p for p in (model_path, data_engine_path, meta_path) if not os.path.exists(p)]
    if missing:
        return False, '사전학습 번들 파일이 없습니다: ' + ', '.join(os.path.basename(p) for p in missing)
    try:
        engine = joblib.load(data_engine_path)
        engine.file_path = None
        if 'Fe' not in engine.get_selected_training_columns():
            return False, '사전학습 입력 컬럼 정보가 올바르지 않습니다.'
        model = ModelEngine(model_type='RF', output_dim=4)
        model.load(model_path)
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except Exception as exc:
        return False, f'사전학습 번들 로드 실패: {exc}'
    pretrained_data_engine = engine
    pretrained_model_engine = model
    pretrained_meta = meta
    return True, ""


def _predict_with(engine_model, engine_data, input_dict):
    """공통 추론 + 고C 보정. (results, correction_info) 반환."""
    scaled_input = engine_data.get_inference_data(input_dict)
    mean_scaled, std_scaled = engine_model.predict(np.asarray(scaled_input, dtype=np.float32))
    mean = np.asarray(engine_data.scaler_y.inverse_transform(mean_scaled))[0]
    std = np.asarray(std_scaled)[0] * np.asarray(engine_data.scaler_y.scale_)
    mean, correction = apply_high_carbon_correction(mean, input_dict)
    if correction.get('applied'):
        std = np.asarray(std, dtype=float)
        std[2] = float(std[2] * correction['factor'])
    results = {
        name: {
            'value': round(float(mean[i]), 2),
            'uncertainty': round(float(std[i]), 2),
        }
        for i, name in enumerate(TARGET_NAMES)
    }
    return results, mean, correction


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@app.route('/status', methods=['GET'])
def get_status():
    pretrained_ok, pretrained_msg = _load_pretrained_bundle()
    return jsonify({
        'file_loaded': bool(data_engine.file_path and os.path.exists(data_engine.file_path or '')),
        'preprocessed': data_engine.df is not None and len(data_engine.df) > 0,
        'model_trained': model_engine is not None,
        'model_type': model_engine.model_type if model_engine else None,
        'samples': int(len(data_engine.df)) if data_engine.df is not None else 0,
        'missing_pct': round(float(data_engine.df.isnull().mean().mean() * 100), 1)
                       if data_engine.df is not None else 0.0,
        'pretrained_available': pretrained_ok,
        'pretrained_error': pretrained_msg if not pretrained_ok else '',
        'pretrained_model_type': pretrained_meta.get('model_type') if pretrained_ok else None,
    })


# ---------------------------------------------------------------------------
# File load
# ---------------------------------------------------------------------------

@app.route('/load', methods=['POST'])
def load_file():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다.'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '빈 파일명입니다.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        data_engine.set_file_path(filepath)
        raw_df = data_engine.load_data()
        rows, cols = raw_df.shape
        missing_pct = round(float(raw_df.isnull().mean().mean() * 100), 1)
        return jsonify({
            'status': 'success',
            'filename': filename,
            'rows': rows,
            'cols': cols,
            'missing_pct': missing_pct,
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

@app.route('/preprocess', methods=['POST'])
def preprocess():
    body = request.json or {}
    missing_strategy = body.get('missing_strategy', 'mean')
    outlier_strategy = body.get('outlier_strategy', 'clip')
    feature_engineering = body.get('feature_engineering', True)

    data_engine.set_quality_options(
        missing_strategy=missing_strategy,
        outlier_strategy=outlier_strategy,
        feature_engineering=feature_engineering,
    )

    try:
        data_engine.preprocess_data()
        df = data_engine.df
        samples = int(len(df)) if df is not None else 0
        missing_pct = round(float(df.isnull().mean().mean() * 100), 1) if df is not None else 0.0
        report = data_engine.last_quality_report or {}
        return jsonify({
            'status': 'success',
            'samples': samples,
            'missing_pct': missing_pct,
            'report': {k: (v if not isinstance(v, np.integer) else int(v))
                       for k, v in report.items()},
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------

@app.route('/data', methods=['GET'])
def get_data():
    if data_engine.df is None or len(data_engine.df) == 0:
        return jsonify({'error': '전처리된 데이터가 없습니다.'}), 400

    limit = int(request.args.get('limit', 200))
    df = data_engine.df.head(limit).round(4)
    columns = df.columns.tolist()
    rows = df.fillna('').to_dict(orient='records')

    return jsonify({
        'columns': columns,
        'rows': rows,
        'total': int(len(data_engine.df)),
    })


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

@app.route('/train', methods=['POST'])
def train():
    global model_engine
    body = request.json or {}
    model_type = body.get('model_type', 'RF')

    if not data_engine.file_path:
        return jsonify({'error': '파일이 로드되지 않았습니다.'}), 400

    try:
        data_engine.load_data()
        X_train, X_test, y_train, y_test_scaled, X_test_raw, y_raw_test = (
            data_engine.preprocess_data()
        )

        if len(X_train) == 0:
            return jsonify({'error': '전처리 후 학습 가능한 데이터가 없습니다.'}), 400

        model_engine = ModelEngine(
            model_type=model_type,
            output_dim=y_train.shape[1],
        )
        model_engine.train(X_train, y_train)

        os.makedirs('models', exist_ok=True)
        model_engine.save('models/material_model.pkl')
        joblib.dump(data_engine, 'models/data_engine.pkl')

        mean_scaled, _ = model_engine.predict(X_test)
        y_pred = data_engine.inverse_transform_y(mean_scaled)

        from sklearn.metrics import r2_score, mean_absolute_error
        r2 = r2_score(y_raw_test, y_pred, multioutput='raw_values')
        mae = mean_absolute_error(y_raw_test, y_pred, multioutput='raw_values')

        target_names = ['yield_stress_mpa', 'uts_mpa', 'elongation_pct', 'area_reduction_pct']
        metrics = {
            name: {'r2': round(float(r2[i]), 4), 'mae': round(float(mae[i]), 2)}
            for i, name in enumerate(target_names)
        }

        return jsonify({'status': 'success', 'model_type': model_type, 'metrics': metrics})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

@app.route('/predict', methods=['POST'])
def predict():
    if not model_engine or data_engine.df is None:
        return jsonify({'error': '모델이 학습되지 않았습니다. 먼저 학습을 실행하세요.'}), 400

    data = request.json
    try:
        results, _mean, correction = _predict_with(model_engine, data_engine, data)
        return jsonify({'status': 'success', 'model_type': model_engine.model_type,
                        'predictions': results, 'correction': correction,
                        'correction_note': correction_badge(correction)})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Pretrained prediction (GUI 사전학습 탭과 동일 번들 + 고C 보정)
# ---------------------------------------------------------------------------

@app.route('/predict/pretrained', methods=['POST'])
def predict_pretrained():
    ok, msg = _load_pretrained_bundle()
    if not ok:
        return jsonify({'error': msg}), 400

    data = request.json or {}
    try:
        results, _mean, correction = _predict_with(
            pretrained_model_engine, pretrained_data_engine, data)
        return jsonify({
            'status': 'success',
            'model_type': pretrained_meta.get('model_type', pretrained_model_engine.model_type),
            'metrics': {k: pretrained_meta.get(k) for k in ('r2_avg', 'mae_avg')},
            'predictions': results,
            'correction': correction,
            'correction_note': correction_badge(correction),
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Stress-strain curve (그래프 데이터를 JSON으로 — 웹 UI용)
# ---------------------------------------------------------------------------

@app.route('/curve', methods=['POST'])
def curve():
    """입력 조성 → 추론 → 곡선 프로파일.

    body: { input: {...}, use_pretrained: true,
            yield_mode: 'continuous'|'discontinuous', luders_strain: 0.02,
            fracture_mode: 'auto'|'ductile'|'brittle' }
    """
    from src.gui.mixins.charts_mixin import ChartsMixin

    body = request.json or {}
    input_dict = body.get('input') or {}
    use_pretrained = body.get('use_pretrained', True)
    yield_mode = body.get('yield_mode', 'continuous')
    luders_strain = body.get('luders_strain')
    fracture_mode = body.get('fracture_mode', 'auto')

    try:
        if use_pretrained:
            ok, msg = _load_pretrained_bundle()
            if not ok:
                return jsonify({'error': msg}), 400
            engine_model, engine_data = pretrained_model_engine, pretrained_data_engine
            model_label = pretrained_meta.get('model_type', 'RF')
        else:
            if not model_engine or data_engine.df is None:
                return jsonify({'error': '모델이 학습되지 않았습니다.'}), 400
            engine_model, engine_data = model_engine, data_engine
            model_label = engine_model.model_type

        _results, mean, correction = _predict_with(engine_model, engine_data, input_dict)
        builder = ChartsMixin()
        strain, stress, points, meta, segments = builder._build_stress_strain_profile(
            np.asarray(mean, dtype=float), dict(input_dict),
            yield_mode=yield_mode, luders_strain=luders_strain,
            fracture_mode=fracture_mode,
        )
        return jsonify({
            'status': 'success',
            'model_type': model_label,
            'correction': correction,
            'correction_note': correction_badge(correction),
            'curve': {
                'strain': [round(float(x), 6) for x in np.asarray(strain).tolist()],
                'stress': [round(float(y), 3) for y in np.asarray(stress).tolist()],
                'points': {k: [round(float(v[0]), 6), round(float(v[1]), 2)]
                           for k, v in points.items()},
                'meta': {k: (round(float(v), 4) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                         for k, v in meta.items()},
                'segments': {k: None for k in segments.keys()},
            },
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    _load_saved_resources()
    print('AI 소재 발굴 API 서버가 5000번 포트에서 시작되었습니다.')
    app.run(host='0.0.0.0', port=5000)
