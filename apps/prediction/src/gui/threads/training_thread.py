import os

import joblib
from PyQt6.QtCore import QThread, pyqtSignal

from src.engine.model_engine import ModelEngine


class TrainingThread(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)

    def __init__(self, data_engine, model_type="RF", max_iter=2000):
        super().__init__()
        self.data_engine = data_engine
        self.model_type = model_type
        self.max_iter = max_iter

    def run(self):
        try:
            self.progress.emit("데이터를 다시 불러오고 전처리하는 중입니다.")
            self.data_engine.load_data()
            self.progress.emit(self.data_engine.format_quality_report())

            X_train, X_test, y_train, _, _, y_raw_test = self.data_engine.preprocess_data()
            if len(X_train) == 0:
                self.finished.emit("전처리 후 학습 가능한 데이터가 없습니다.")
                return

            self.progress.emit(f"{self.model_type} 모델을 초기화하는 중입니다.")
            model_engine = ModelEngine(
                model_type=self.model_type,
                output_dim=y_train.shape[1],
                max_iter=self.max_iter,
            )

            self.progress.emit(f"{self.model_type} 모델을 학습하는 중입니다.")
            model_engine.train(X_train, y_train)

            if not os.path.exists("models"):
                os.makedirs("models")
            model_engine.save("models/material_model.pkl")
            joblib.dump(self.data_engine, "models/data_engine.pkl")

            self.progress.emit("학습 결과를 평가하는 중입니다.")
            mean_scaled, _ = model_engine.predict(X_test)
            y_pred = self.data_engine.inverse_transform_y(mean_scaled)

            from sklearn.metrics import mean_absolute_error, r2_score

            r2 = r2_score(y_raw_test, y_pred, multioutput="raw_values")
            mae = mean_absolute_error(y_raw_test, y_pred, multioutput="raw_values")

            self.finished.emit(
                {
                    "model": model_engine,
                    "metrics": {"r2": r2, "mae": mae},
                    "y_test": y_raw_test,
                    "y_pred": y_pred,
                    "quality_report": self.data_engine.last_quality_report,
                }
            )
        except Exception as exc:
            self.finished.emit(f"학습 중 오류가 발생했습니다: {exc}")
