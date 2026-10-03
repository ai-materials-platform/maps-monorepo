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

# 실행 위치와 무관하게 고정: 업로드/모델은 apps/prediction 아래,
# 워크스페이스는 모노레포 루트 projects/
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
UPLOAD_FOLDER = os.path.join(APP_DIR, 'data', 'uploads')
MODELS_DIR = os.path.join(APP_DIR, 'models')

app = Flask(__name__)
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

data_engine = DataEngine(None)
model_engine = None

# 사전학습 번들 (GUI 사전학습 탭과 동일 파일)
pretrained_model_engine = None
pretrained_data_engine = None
pretrained_meta = {}


def _load_saved_resources():
    global data_engine, model_engine
    engine_path = os.path.join(MODELS_DIR, 'data_engine.pkl')
    model_path = os.path.join(MODELS_DIR, 'material_model.pkl')
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

    if not data_engine.file_path:
        return jsonify({'error': '파일이 로드되지 않았습니다. 먼저 /load로 업로드하세요.'}), 400

    data_engine.configure_quality_rules(
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
        model_engine.save(os.path.join(MODELS_DIR, 'material_model.pkl'))
        joblib.dump(data_engine, os.path.join(MODELS_DIR, 'data_engine.pkl'))

        # 레지스트리: 타임스탬프 이름으로 모델+데이터엔진 쌍 보관 (재시작 후에도 선택 가능)
        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        reg_name = f"custom-{model_type}-{stamp}"
        model_engine.save(os.path.join(MODELS_DIR, f'{reg_name}.model.pkl'))
        joblib.dump(data_engine, os.path.join(MODELS_DIR, f'{reg_name}.data.pkl'))
        reg_meta = {
            'name': reg_name,
            'model_type': model_type,
            'saved_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'samples': int(len(X_train)),
        }

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
        reg_meta['metrics'] = metrics
        try:
            with open(os.path.join(MODELS_DIR, f'{reg_name}.meta.json'), 'w', encoding='utf-8') as f:
                json.dump(reg_meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return jsonify({'status': 'success', 'model_type': model_type,
                        'metrics': metrics, 'model_name': reg_name})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Model registry (학습된 커스텀 모델 목록/선택)
# ---------------------------------------------------------------------------

_custom_cache = {}


def _list_custom_models():
    items = []
    try:
        names = sorted(os.listdir(MODELS_DIR))
    except Exception:
        return items
    for fname in names:
        if not fname.endswith('.meta.json') or not fname.startswith('custom-'):
            continue
        name = fname[:-len('.meta.json')]
        model_path = os.path.join(MODELS_DIR, name + '.model.pkl')
        data_path = os.path.join(MODELS_DIR, name + '.data.pkl')
        if not (os.path.exists(model_path) and os.path.exists(data_path)):
            continue
        try:
            with open(os.path.join(MODELS_DIR, fname), 'r', encoding='utf-8') as f:
                meta = json.load(f)
        except Exception:
            meta = {}
        items.append({
            'name': name,
            'model_type': meta.get('model_type', '?'),
            'saved_date': meta.get('saved_date', ''),
            'samples': meta.get('samples', 0),
            'metrics': meta.get('metrics', {}),
        })
    items.sort(key=lambda m: m['name'], reverse=True)
    return items


def _load_custom_model(name):
    """(model_engine, data_engine) 반환. 없으면 (None, None)."""
    if name in _custom_cache:
        return _custom_cache[name]
    model_path = os.path.join(MODELS_DIR, name + '.model.pkl')
    data_path = os.path.join(MODELS_DIR, name + '.data.pkl')
    if '..' in name or '/' in name or '\\' in name:
        return None, None
    if not (os.path.exists(model_path) and os.path.exists(data_path)):
        return None, None
    try:
        model = ModelEngine(model_type='RF', output_dim=4)
        model.load(model_path)
        data = joblib.load(data_path)
    except Exception:
        return None, None
    _custom_cache[name] = (model, data)
    return model, data


@app.route('/models', methods=['GET'])
def list_models():
    ok, _msg = _load_pretrained_bundle()
    items = []
    if ok:
        items.append({
            'name': 'pretrained',
            'model_type': pretrained_meta.get('model_type', 'RF'),
            'saved_date': 'bundled',
            'samples': None,
            'metrics': {k: pretrained_meta.get(k) for k in ('r2_avg', 'mae_avg')},
        })
    items.extend(_list_custom_models())
    return jsonify({'status': 'success', 'models': items})


@app.route('/predict/custom', methods=['POST'])
def predict_custom():
    body = request.json or {}
    name = body.get('model', '')
    data = body.get('input') or {}
    if not name:
        return jsonify({'error': 'model 이름을 지정하세요.'}), 400
    model, engine_data = _load_custom_model(name)
    if model is None:
        return jsonify({'error': f'모델을 찾을 수 없습니다: {name}'}), 404
    try:
        results, _mean, correction = _predict_with(model, engine_data, data)
        return jsonify({
            'status': 'success', 'model_name': name, 'model_type': model.model_type,
            'predictions': results, 'correction': correction,
            'correction_note': correction_badge(correction),
        })
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
# Workspaces (모노레포 루트 projects/ — GUI workspaces/와 별도)
# ---------------------------------------------------------------------------

def _workspace_root():
    env = os.environ.get('AI_MAPS_WORKSPACE_ROOT')
    if env:
        return os.path.abspath(env)
    here = os.path.abspath(os.path.dirname(__file__))  # src/api
    return os.path.abspath(os.path.join(here, '..', '..', '..', '..', 'projects'))


def _check_workspace_name(name):
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()
    if name in ('.', '..') or '/' in name or '\\' in name:
        return None
    return name


def _workspace_summary(folder):
    info = {'name': os.path.basename(folder)}
    state_path = os.path.join(folder, 'state.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        info['saved_date'] = state.get('saved_date', '')
        info['has_prediction'] = 'predictions' in state or 'prediction_mean' in state
    except Exception:
        info['saved_date'] = ''
        info['has_prediction'] = False
    return info


@app.route('/workspaces', methods=['GET'])
def list_workspaces():
    root = _workspace_root()
    os.makedirs(root, exist_ok=True)
    items = []
    for entry in sorted(os.listdir(root)):
        folder = os.path.join(root, entry)
        if os.path.isdir(folder):
            items.append(_workspace_summary(folder))
    return jsonify({'status': 'success', 'workspaces': items})


@app.route('/workspaces', methods=['POST'])
def save_workspace():
    body = request.json or {}
    name = _check_workspace_name(body.get('name', ''))
    if not name:
        return jsonify({'error': '유효한 이름이 필요합니다. (/, \\, .. 불가)'}), 400
    root = _workspace_root()
    os.makedirs(root, exist_ok=True)
    folder = os.path.join(root, name)
    if os.path.exists(folder) and not body.get('overwrite', False):
        return jsonify({'error': f"'{name}'이(가) 이미 존재합니다.", 'exists': True}), 409
    os.makedirs(folder, exist_ok=True)
    state = {
        'name': name,
        'saved_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'input': body.get('input') or {},
        'predictions': body.get('predictions') or {},
        'correction': body.get('correction') or {},
        'curve_params': body.get('curve_params') or {},
    }
    try:
        with open(os.path.join(folder, 'state.json'), 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
    return jsonify({'status': 'success', 'name': name})


@app.route('/workspaces/<name>', methods=['GET'])
def load_workspace(name):
    checked = _check_workspace_name(name)
    if not checked:
        return jsonify({'error': '유효하지 않은 이름입니다.'}), 400
    state_path = os.path.join(_workspace_root(), checked, 'state.json')
    if not os.path.exists(state_path):
        return jsonify({'error': '워크스페이스를 찾을 수 없습니다.'}), 404
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
    return jsonify({'status': 'success', 'workspace': state})


@app.route('/workspaces/<name>', methods=['DELETE'])
def delete_workspace(name):
    import shutil
    checked = _check_workspace_name(name)
    if not checked:
        return jsonify({'error': '유효하지 않은 이름입니다.'}), 400
    folder = os.path.join(_workspace_root(), checked)
    if not os.path.isdir(folder):
        return jsonify({'error': '워크스페이스를 찾을 수 없습니다.'}), 404
    try:
        shutil.rmtree(folder)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
    return jsonify({'status': 'success', 'name': checked})

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
