import os
import datetime
import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from src.engine.data_engine import DataEngine
from src.engine.model_engine import ModelEngine

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'data/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

data_engine = DataEngine(None)
model_engine = None


def _load_saved_resources():
    global data_engine, model_engine
    engine_path = 'models/data_engine.pkl'
    model_path = 'models/material_model.pkl'
    if os.path.exists(engine_path):
        data_engine = joblib.load(engine_path)
    if os.path.exists(model_path):
        model_engine = ModelEngine(model_type='RF', output_dim=4)
        model_engine.load(model_path)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        'file_loaded': bool(data_engine.file_path and os.path.exists(data_engine.file_path or '')),
        'preprocessed': data_engine.df is not None and len(data_engine.df) > 0,
        'model_trained': model_engine is not None,
        'model_type': model_engine.model_type if model_engine else None,
        'samples': int(len(data_engine.df)) if data_engine.df is not None else 0,
        'missing_pct': round(float(data_engine.df.isnull().mean().mean() * 100), 1)
                       if data_engine.df is not None else 0.0,
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
        scaled_input = data_engine.get_inference_data(data)
        mean_scaled, std_scaled = model_engine.predict(scaled_input)
        mean = data_engine.scaler_y.inverse_transform(mean_scaled)
        std = std_scaled * data_engine.scaler_y.scale_

        target_names = ['yield_stress_mpa', 'uts_mpa', 'elongation_pct', 'area_reduction_pct']
        results = {
            name: {
                'value': round(float(mean[0, i]), 2),
                'uncertainty': round(float(std[0, i]), 2),
            }
            for i, name in enumerate(target_names)
        }

        return jsonify({'status': 'success', 'model_type': model_engine.model_type, 'predictions': results})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    _load_saved_resources()
    print('AI 소재 발굴 API 서버가 5000번 포트에서 시작되었습니다.')
    app.run(host='0.0.0.0', port=5000)
