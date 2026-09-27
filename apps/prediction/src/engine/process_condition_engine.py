"""
공정 조건 예측기 엔진
합금 조성을 고정하고 공정/조직 조건을 변경하며 기계적 물성을 예측.
RF, XGBoost, LightGBM, CatBoost 학습 후 최고 정확도 모델을 자동 선택.
"""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.multioutput import MultiOutputRegressor

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from lightgbm import LGBMRegressor
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from catboost import CatBoostRegressor
    HAS_CAT = True
except ImportError:
    HAS_CAT = False

# 기본 공정 조건 피처 (항상 포함)
CORE_FEATURES = [
    'solution_treatment_temp',   # 고용화 열처리 온도 (K)
    'cooling_method',            # 냉각 방식: 0=로냉, 1=공냉, 2=수냉
    'annealed',                  # 어닐링 여부 (0/1)
    'tempered',                  # 템퍼링 여부 (0/1)
    'quenched',                  # 급랭 여부 (0/1)
    'Ni_eq',                     # 오스테나이트 안정성 지표
    'Cr_eq',                     # 페라이트 안정성 지표
]

TARGETS = [
    '0.2%proof_stress (M Pa)',
    'UTS (M Pa)',
    'Elongation (%)',
    'Area_reduction (%)',
]

TARGET_DISPLAY = ['항복강도 (MPa)', 'UTS (MPa)', '연신율 (%)', '단면감소율 (%)']

CORE_DEFAULTS = {
    'solution_treatment_temp': '1323',
    'cooling_method': '2',
    'annealed': '0',
    'tempered': '0',
    'quenched': '1',
    'Ni_eq': '13.5',
    'Cr_eq': '19.7',
}

# 옵션 피처 우선순위 (데이터에 존재할 경우 "+추가" 목록 상단에 표시)
_OPTIONAL_PRIORITY = [
    'solution_treatment_time',
    'grains_mm2',
    'test_temperature',
    'type_of_melting',
    'size_of_ingot',
    'product_form',
    'Cr_Ni_ratio',
    'C_plus_N',
    'Cr', 'Ni', 'Mo', 'Mn', 'Si', 'C', 'N', 'Fe',
    'Nb', 'Ti', 'Cu', 'V', 'W', 'Co', 'Al',
]


class ProcessConditionEngine:
    """공정 조건 기반 물성 예측 엔진."""

    def __init__(self):
        self.df_raw = None
        self._data_path = None
        self.feature_cols = None
        self.extra_features = []
        self.best_model = None
        self.best_model_name = None
        self.model_results = {}
        self.scaler_x = StandardScaler()
        self.scaler_y = StandardScaler()
        self.used_targets = TARGETS[:]

    # ------------------------------------------------------------------
    # 데이터 로드
    # ------------------------------------------------------------------

    def _find_data_path(self):
        import glob as _glob
        base = Path(__file__).parent.parent.parent
        for fname in ('STMECH_AUS_SS.xls', 'STMECH_AUS_SS.xlsx'):
            # 직접 경로 먼저 확인
            direct = base / 'data' / 'raw' / fname
            if direct.exists():
                return str(direct)
            # 재귀 검색 (중첩 폴더 대응)
            matches = _glob.glob(str(base / '**' / fname), recursive=True)
            if matches:
                return matches[0]
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다: {base}/**/STMECH_AUS_SS.xls[x]"
        )

    def load_data(self, path=None):
        if path is None:
            path = self._find_data_path()
        self._data_path = path

        try:
            df = pd.read_excel(path, header=5, engine='openpyxl')
        except Exception:
            df = pd.read_excel(path, header=5, engine='xlrd')

        df.columns = [str(c).strip() for c in df.columns]
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = self._derive_process_features(df)
        df = self._compute_equivalents(df)
        self.df_raw = df
        return df

    def _derive_process_features(self, df):
        if 'Solution_treatment_temperature' in df.columns:
            df['solution_treatment_temp'] = df['Solution_treatment_temperature']

        wq_col = 'Water_Quenched_after_s.t.'
        aq_col = 'Air_Quenched_after_s.t.'
        water = df[wq_col].fillna(0).astype(int) if wq_col in df.columns else pd.Series(0, index=df.index)
        air = df[aq_col].fillna(0).astype(int) if aq_col in df.columns else pd.Series(0, index=df.index)

        df['quenched'] = water
        df['annealed'] = ((water == 0) & (air == 0)).astype(int)
        df['tempered'] = 0

        df['cooling_method'] = 0
        df.loc[air == 1, 'cooling_method'] = 1
        df.loc[water == 1, 'cooling_method'] = 2

        renames = {
            'Solution_treatment_time(s)': 'solution_treatment_time',
            'Grains mm-2': 'grains_mm2',
            'Type of melting': 'type_of_melting',
            'Size of ingot': 'size_of_ingot',
            'Product form': 'product_form',
            'Temperature (K)': 'test_temperature',
        }
        for src, dst in renames.items():
            if src in df.columns:
                df[dst] = df[src]

        return df

    def _compute_equivalents(self, df):
        def g(col):
            return df.get(col, pd.Series(0, index=df.index)).fillna(0)

        df['Ni_eq'] = g('Ni') + 30 * g('C') + 0.5 * g('Mn') + 30 * g('N') + 0.3 * g('Cu')
        df['Cr_eq'] = g('Cr') + g('Mo') + 1.5 * g('Si') + 0.5 * g('Nb')
        ni_eq = df['Ni_eq'].replace(0, np.nan)
        df['Cr_Ni_ratio'] = df['Cr_eq'] / ni_eq
        df['C_plus_N'] = g('C') + g('N')
        return df

    # ------------------------------------------------------------------
    # 사용 가능 추가 피처 목록
    # ------------------------------------------------------------------

    def get_available_extra_features(self):
        if self.df_raw is None:
            self.load_data()

        reserved = set(CORE_FEATURES) | set(TARGETS) | {
            'Solution_treatment_temperature',
            'Water_Quenched_after_s.t.',
            'Air_Quenched_after_s.t.',
        }
        available = [
            col for col in self.df_raw.columns
            if col not in reserved and self.df_raw[col].notna().sum() >= 20
        ]
        ordered = [c for c in _OPTIONAL_PRIORITY if c in available]
        rest = [c for c in available if c not in ordered]
        return ordered + rest

    # ------------------------------------------------------------------
    # 학습
    # ------------------------------------------------------------------

    def train(self, extra_features=None):
        if self.df_raw is None:
            self.load_data()

        self.extra_features = extra_features or []
        self.feature_cols = CORE_FEATURES + [
            f for f in self.extra_features if f not in CORE_FEATURES
        ]
        self.feature_cols = [c for c in self.feature_cols if c in self.df_raw.columns]

        existing_targets = [t for t in TARGETS if t in self.df_raw.columns]
        if not existing_targets:
            raise ValueError("타겟 컬럼을 찾을 수 없습니다.")
        self.used_targets = existing_targets

        df_clean = self.df_raw[self.feature_cols + existing_targets].dropna()
        if len(df_clean) < 20:
            raise ValueError(
                f"학습 가능한 샘플이 너무 적습니다 ({len(df_clean)}개). 최소 20개 필요."
            )

        X = df_clean[self.feature_cols].values
        y = df_clean[existing_targets].values
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

        X_tr_s = pd.DataFrame(self.scaler_x.fit_transform(X_tr), columns=self.feature_cols)
        X_te_s = pd.DataFrame(self.scaler_x.transform(X_te), columns=self.feature_cols)
        y_tr_s = self.scaler_y.fit_transform(y_tr)

        models = {
            'RF': MultiOutputRegressor(
                RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
            ),
        }
        if HAS_XGB:
            models['XGBoost'] = MultiOutputRegressor(
                XGBRegressor(n_estimators=200, random_state=42, verbosity=0, n_jobs=-1)
            )
        if HAS_LGB:
            models['LightGBM'] = MultiOutputRegressor(
                LGBMRegressor(n_estimators=200, random_state=42, verbose=-1, n_jobs=-1)
            )
        if HAS_CAT:
            models['CatBoost'] = MultiOutputRegressor(
                CatBoostRegressor(iterations=200, random_state=42, verbose=0)
            )

        print('\n' + '=' * 65)
        print('  공정 조건 예측기 — 모델 학습 결과')
        print('=' * 65)
        print(f'  피처({len(self.feature_cols)}개): {self.feature_cols}')
        print(f'  학습 샘플: {len(X_tr)}, 테스트 샘플: {len(X_te)}')
        print('-' * 65)

        self.model_results = {}
        best_r2 = -np.inf

        for name, model in models.items():
            model.fit(X_tr_s, y_tr_s)
            y_pred_s = model.predict(X_te_s)
            y_pred = self.scaler_y.inverse_transform(y_pred_s)

            r2 = [r2_score(y_te[:, i], y_pred[:, i]) for i in range(y.shape[1])]
            mae = [mean_absolute_error(y_te[:, i], y_pred[:, i]) for i in range(y.shape[1])]
            r2_avg = float(np.mean(r2))
            mae_avg = float(np.mean(mae))

            self.model_results[name] = {
                'model': model,
                'r2_avg': r2_avg,
                'r2_per_target': r2,
                'mae_avg': mae_avg,
                'mae_per_target': mae,
                'y_test': y_te,
                'y_pred': y_pred,
            }

            print(f'  [{name}]  평균 R²={r2_avg:.4f}  평균 MAE={mae_avg:.2f}')
            for i, t in enumerate(existing_targets):
                print(f'    {t}: R²={r2[i]:.4f}, MAE={mae[i]:.2f}')

            if r2_avg > best_r2:
                best_r2 = r2_avg
                self.best_model = model
                self.best_model_name = name

        print('-' * 65)
        best = self.best_model_name
        print(
            f'  ★ 최적 모델: {best}  '
            f'(평균 R²={self.model_results[best]["r2_avg"]:.4f}, '
            f'평균 MAE={self.model_results[best]["mae_avg"]:.2f})'
        )
        print('=' * 65 + '\n')

        return self.model_results

    # ------------------------------------------------------------------
    # 예측
    # ------------------------------------------------------------------

    def predict(self, input_dict):
        if self.best_model is None:
            raise RuntimeError("먼저 학습을 실행해 주세요.")
        # DataFrame으로 전달해 LightGBM 피처 이름 경고 방지
        row_df = pd.DataFrame(
            [[float(input_dict.get(col, 0)) for col in self.feature_cols]],
            columns=self.feature_cols,
        )
        row_s = self.scaler_x.transform(row_df.values)
        row_s_df = pd.DataFrame(row_s, columns=self.feature_cols)
        pred_s = self.best_model.predict(row_s_df)
        pred = self.scaler_y.inverse_transform(pred_s)[0]
        return {t: float(pred[i]) for i, t in enumerate(self.used_targets)}

    # ------------------------------------------------------------------
    # 특성 중요도
    # ------------------------------------------------------------------

    def get_feature_importance(self):
        if self.best_model is None:
            return {}
        try:
            imps = np.mean(
                [est.feature_importances_ for est in self.best_model.estimators_],
                axis=0,
            )
            total = imps.sum()
            if total > 0:
                imps = imps / total
            return dict(zip(self.feature_cols, imps))
        except AttributeError:
            return {}

    # ------------------------------------------------------------------
    # 저장 / 불러오기
    # ------------------------------------------------------------------

    def save(self, path='models/process_condition_model.pkl'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path='models/process_condition_model.pkl'):
        return joblib.load(path)
