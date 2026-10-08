import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.multioutput import MultiOutputRegressor
from scipy.optimize import minimize


def _fit_affine_std(resid, std):
    """σ' = a + b·σ (a, b ≥ 0)를 가우시안 NLL 최소화로 맞춘다 (출력 하나)."""
    b0 = np.sqrt(np.mean(np.square(resid / (std + 1e-9))))  # 계수만 곱하는 경우의 해 = 시작점

    def nll(p):
        sig = p[0] + p[1] * std + 1e-9
        return np.sum(np.log(sig) + np.square(resid) / (2 * np.square(sig)))

    res = minimize(nll, x0=[0.0, b0], bounds=[(0.0, None), (0.0, None)], method="L-BFGS-B")
    return res.x if res.success else np.array([0.0, b0])

class ModelEngine:
    def __init__(self, model_type='RF', output_dim=2, max_iter=2000):
        self.model_type = model_type
        self.output_dim = output_dim
        self.max_iter = max_iter
        self.model = self._create_model(model_type)
        self.is_trained = False
        # 출력별 불확실도 보정 σ' = a + b·σ — shape (2, output): [a, b].
        # 앙상블/트리 편차는 '모델끼리 얼마나 다른가'라 실제 오차와 크기가 안 맞는다.
        # 계수만 곱하면(σ·b) 평균 포함률은 맞지만 TFP는 σ가 큰 구간을 1.7배 과대추정 —
        # 절편 a를 더해 기울기를 완만하게 하면 큰 구간이 1.04배로 맞는다 (PR 본문 비교표).
        # None = 예전 저장 형식 → 기존처럼 편차만.
        self.std_affine = None
        
    def _create_model(self, model_type):
        if model_type == 'RF':
            return RandomForestRegressor(n_estimators=100)
        elif model_type == 'GBM':
            # Gradient Boosting wrap
            return MultiOutputRegressor(GradientBoostingRegressor(n_estimators=100))
        elif model_type == 'MLP':
            return MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=self.max_iter, 
                                early_stopping=True, validation_fraction=0.1, n_iter_no_change=10)
        elif model_type == 'TFP':
            # Bootstrapped MLP Ensemble with Early Stopping enabled
            models = [MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=self.max_iter, 
                                   early_stopping=True, validation_fraction=0.1, 
                                   n_iter_no_change=10, random_state=i) for i in range(5)]
            return models
        else:
            return RandomForestRegressor(n_estimators=100, random_state=42)
            
    def train(self, X_train, y_train, X_val=None, y_val=None):
        if self.model_type == 'TFP':
            # Train each model in the ensemble with a different bootstrap sample
            n_samples = X_train.shape[0]
            for m in self.model:
                indices = np.random.choice(n_samples, n_samples, replace=True)
                m.fit(X_train[indices], y_train[indices])
        else:
            self.model.fit(X_train, y_train)
            
        self.is_trained = True
        if X_val is not None and y_val is not None:
            mean_val, std_val = self._predict_raw(X_val)
            resid = np.asarray(y_val) - np.asarray(mean_val)
            std_val = np.asarray(std_val)
            self.std_affine = np.column_stack(
                [_fit_affine_std(resid[:, j], std_val[:, j]) for j in range(resid.shape[1])]
            )

        class History:
            def __init__(self):
                self.history = {'loss': [0]}
        return History()

    def predict(self, X):
        """(mean, std) — std는 검증 세트로 보정한 a + b·σ. 보정값이 없으면 원래 편차."""
        mean, std = self._predict_raw(X)
        if self.std_affine is not None:
            std = self.std_affine[0] + self.std_affine[1] * std
        return mean, std

    def _predict_raw(self, X):
        if not self.is_trained:
            raise Exception("Model not trained yet.")

        if self.model_type == 'TFP':
            # Collect predictions from all models in the ensemble
            all_preds = np.array([m.predict(X) for m in self.model])
            mean = np.mean(all_preds, axis=0)
            std = np.std(all_preds, axis=0)
            return mean, std
        
        mean = self.model.predict(X)
        
        if self.model_type == 'RF':
            all_tree_preds = []
            for tree in self.model.estimators_:
                all_tree_preds.append(tree.predict(X))
            all_tree_preds = np.array(all_tree_preds)
            std = np.std(all_tree_preds, axis=0)
        else:
            # Heuristic for GBM/MLP (standard deviation estimate)
            std = np.abs(mean) * 0.05
            
        return mean, std

    def save(self, path):
        joblib.dump({"model": self.model, "type": self.model_type, "std_affine": self.std_affine}, path)

    def load(self, path):
        data = joblib.load(path)
        self.model = data["model"]
        self.model_type = data.get("type", "RF")
        self.std_affine = data.get("std_affine")
        if self.std_affine is None and data.get("std_scale") is not None:
            # #11 형식(계수만) → a=0, b=계수
            self.std_affine = np.vstack([np.zeros_like(data["std_scale"]), data["std_scale"]])
        self.is_trained = True
