import csv
import json
import os

import joblib
import numpy as np
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from src.engine.model_engine import ModelEngine


class InferenceMixin:
    def _run_prediction(
        self,
        model_engine,
        data_engine,
        inputs,
        result_label,
        canvas,
        curve_canvas=None,
        curve_label=None,
        prediction_state_attr=None,
        result_tabs=None,
        simulation_prefix=None,
    ):
        if not model_engine or not data_engine:
            result_label.setText(
                "<b>먼저 모델을 준비해 주세요.</b><br>"
                "학습을 완료하거나 저장된 모델을 불러온 뒤 예측을 실행할 수 있습니다."
            )
            return None

        input_dict = {key: widget.text() for key, widget in inputs.items()}
        scaled_input = data_engine.get_inference_data(input_dict)
        mean_scaled, std_scaled = model_engine.predict(scaled_input.astype(np.float32))

        mean = data_engine.scaler_y.inverse_transform(mean_scaled)[0]
        std = std_scaled[0] * data_engine.scaler_y.scale_

        # --- 파생 분석 지표 계산 ---
        ys_uts_ratio = mean[0] / max(mean[1], 1.0)
        sd_index = mean[1] * mean[2]   # 강도×연성 지수 (MPa·%)

        if ys_uts_ratio < 0.50:
            ratio_tag = "가공경화 여유 충분"
        elif ys_uts_ratio < 0.72:
            ratio_tag = "표준적 가공경화 거동"
        else:
            ratio_tag = "가공경화 여유 제한적"

        if sd_index > 40000:
            sd_tag = "우수"
        elif sd_index > 25000:
            sd_tag = "양호"
        else:
            sd_tag = "보통"

        # 재료 상태 추정
        if ys_uts_ratio < 0.55 and mean[2] > 50:
            state_tag = "완전 소둔(annealed) 상태로 추정"
        elif ys_uts_ratio > 0.72 or mean[2] < 28:
            state_tag = "가공경화 또는 고강도 조건으로 추정"
        else:
            state_tag = "표준 열처리 조건으로 추정"

        # 평균 상대 불확실도 (CV%)
        cv_per = [std[i] / max(abs(mean[i]), 1.0) * 100 for i in range(4)]
        avg_cv = float(np.mean(cv_per))
        if avg_cv < 5:
            conf_tag = "높음"
        elif avg_cv < 12:
            conf_tag = "보통"
        else:
            conf_tag = "낮음 — 추가 데이터 권장"

        c = self._theme()
        note_color = c["text_label"]
        result_text = (
            f"<b>강도</b>&nbsp;&nbsp;"
            f"항복강도: <b>{mean[0]:.1f} ± {std[0]:.1f} MPa</b>&ensp;"
            f"UTS: <b>{mean[1]:.1f} ± {std[1]:.1f} MPa</b><br>"
            f"<b>연성</b>&nbsp;&nbsp;"
            f"연신율: <b>{mean[2]:.1f} ± {std[2]:.1f} %</b>&ensp;"
            f"단면감소율: <b>{mean[3]:.1f} ± {std[3]:.1f} %</b>"
            f"<hr style='border:none;border-top:1px solid {c['border']};margin:6px 0;'>"
            f"<b>분석 요약</b><br>"
            f"YS / UTS: <b>{ys_uts_ratio:.2f}</b> &mdash; {ratio_tag}<br>"
            f"강도×연성 지수: <b>{sd_index:,.0f} MPa·%</b> ({sd_tag})<br>"
            f"재료 상태: {state_tag}<br>"
            f"예측 신뢰도: <b>{conf_tag}</b>"
            f" <span style='color:{note_color};'>(평균 CV {avg_cv:.1f}%)</span>"
        )
        result_label.setText(result_text)
        self._render_prediction_chart(canvas, mean, std)
        if curve_canvas is not None and curve_label is not None:
            self._render_stress_strain_curve(curve_canvas, curve_label, mean, input_dict)
        if simulation_prefix:
            self._render_simulation_view(simulation_prefix, mean, input_dict)
        if prediction_state_attr:
            setattr(
                self,
                prediction_state_attr,
                {
                    "mean": np.array(mean, dtype=float),
                    "std": np.array(std, dtype=float),
                    "input_dict": dict(input_dict),
                },
            )

        if result_tabs is not None:
            result_tabs.setCurrentIndex(0)

        if prediction_state_attr == "_pretrained_prediction_state" and hasattr(self, "pretrained_export_btn"):
            self.pretrained_export_btn.setEnabled(True)
        elif prediction_state_attr == "_user_prediction_state" and hasattr(self, "user_export_btn"):
            self.user_export_btn.setEnabled(True)

        return {
            "yield_stress": round(float(mean[0]), 2),
            "uts": round(float(mean[1]), 2),
            "elongation": round(float(mean[2]), 2),
            "area_reduction": round(float(mean[3]), 2),
        }

    def _restore_prediction_display(self, mean, std, input_dict, target="user"):
        """불러오기 시 저장된 mean/std/input_dict로 result_display 텍스트와 prediction_state 복원."""
        mean = [float(x) for x in mean]
        std = [float(x) for x in std]
        ys_uts_ratio = mean[0] / max(mean[1], 1.0)
        sd_index = mean[1] * mean[2]
        if ys_uts_ratio < 0.50:
            ratio_tag = "가공경화 여유 충분"
        elif ys_uts_ratio < 0.72:
            ratio_tag = "표준적 가공경화 거동"
        else:
            ratio_tag = "가공경화 여유 제한적"
        if sd_index > 40000:
            sd_tag = "우수"
        elif sd_index > 25000:
            sd_tag = "양호"
        else:
            sd_tag = "보통"
        if ys_uts_ratio < 0.55 and mean[2] > 50:
            state_tag = "완전 소둔(annealed) 상태로 추정"
        elif ys_uts_ratio > 0.72 or mean[2] < 28:
            state_tag = "가공경화 또는 고강도 조건으로 추정"
        else:
            state_tag = "표준 열처리 조건으로 추정"
        cv_per = [std[i] / max(abs(mean[i]), 1.0) * 100 for i in range(4)]
        avg_cv = float(np.mean(cv_per))
        if avg_cv < 5:
            conf_tag = "높음"
        elif avg_cv < 12:
            conf_tag = "보통"
        else:
            conf_tag = "낮음 — 추가 데이터 권장"
        c = self._theme()
        note_color = c["text_label"]
        result_text = (
            f"<b>강도</b>&nbsp;&nbsp;"
            f"항복강도: <b>{mean[0]:.1f} ± {std[0]:.1f} MPa</b>&ensp;"
            f"UTS: <b>{mean[1]:.1f} ± {std[1]:.1f} MPa</b><br>"
            f"<b>연성</b>&nbsp;&nbsp;"
            f"연신율: <b>{mean[2]:.1f} ± {std[2]:.1f} %</b>&ensp;"
            f"단면감소율: <b>{mean[3]:.1f} ± {std[3]:.1f} %</b>"
            f"<hr style='border:none;border-top:1px solid {c['border']};margin:6px 0;'>"
            f"<b>분석 요약</b><br>"
            f"YS / UTS: <b>{ys_uts_ratio:.2f}</b> &mdash; {ratio_tag}<br>"
            f"강도×연성 지수: <b>{sd_index:,.0f} MPa·%</b> ({sd_tag})<br>"
            f"재료 상태: {state_tag}<br>"
            f"예측 신뢰도: <b>{conf_tag}</b>"
            f" <span style='color:{note_color};'>(평균 CV {avg_cv:.1f}%)</span>"
        )
        state_obj = {
            "mean": np.array(mean, dtype=float),
            "std": np.array(std, dtype=float),
            "input_dict": dict(input_dict),
        }
        mean_arr = np.array(mean, dtype=float)
        std_arr = np.array(std, dtype=float)
        if target == "pretrained":
            if hasattr(self, "pretrained_result_display"):
                self.pretrained_result_display.setText(result_text)
            self._pretrained_prediction_state = state_obj
            if hasattr(self, "pretrained_export_btn"):
                self.pretrained_export_btn.setEnabled(True)
            if hasattr(self, "pretrained_prediction_canvas"):
                self._render_prediction_chart(self.pretrained_prediction_canvas, mean_arr, std_arr)
            if hasattr(self, "pretrained_curve_canvas") and hasattr(self, "pretrained_curve_placeholder"):
                self._render_stress_strain_curve(
                    self.pretrained_curve_canvas,
                    self.pretrained_curve_placeholder,
                    mean_arr,
                    input_dict,
                )
        else:
            if hasattr(self, "result_display"):
                self.result_display.setText(result_text)
            self._user_prediction_state = state_obj
            if hasattr(self, "user_export_btn"):
                self.user_export_btn.setEnabled(True)
            if hasattr(self, "prediction_canvas"):
                self._render_prediction_chart(self.prediction_canvas, mean_arr, std_arr)
            if hasattr(self, "stress_strain_canvas") and hasattr(self, "stress_strain_placeholder_label"):
                self._render_stress_strain_curve(
                    self.stress_strain_canvas,
                    self.stress_strain_placeholder_label,
                    mean_arr,
                    input_dict,
                )

    def on_pretrained_predict_clicked(self):
        try:
            self._run_prediction(
                self.pretrained_model_engine,
                self.pretrained_data_engine,
                self.pretrained_inputs,
                self.pretrained_result_display,
                self.pretrained_prediction_canvas,
                self.pretrained_curve_canvas,
                self.pretrained_curve_placeholder,
                "_pretrained_prediction_state",
                self.pretrained_result_tabs,
                "pretrained",
            )
        except Exception as exc:
            self.pretrained_result_display.setText(f"<b>사전학습 모델 예측 중 오류가 발생했습니다.</b><br>{exc}")

    def on_predict_clicked(self):
        try:
            results = self._run_prediction(
                self.model_engine,
                self.data_engine,
                self.inputs,
                self.result_display,
                self.prediction_canvas,
                self.stress_strain_canvas,
                self.stress_strain_placeholder_label,
                "_user_prediction_state",
                self.inference_result_tabs,
                "user",
            )
            if results is None:
                return

            auto_folder = os.path.join("workspaces", "auto_save")
            if os.path.exists(auto_folder):
                self.prediction_canvas.fig.savefig(
                    os.path.join(auto_folder, "prediction.png"), dpi=200, bbox_inches="tight"
                )
                self.stress_strain_canvas.fig.savefig(
                    os.path.join(auto_folder, "stress_strain_curve.png"), dpi=200, bbox_inches="tight"
                )

            self.append_log({
                "type": "예측",
                "model": self.model_type,
                "inputs": {k: v.text() for k, v in self.inputs.items()},
                "results": results,
            })
        except Exception as exc:
            self.result_display.setText(f"<b>예측 중 오류가 발생했습니다.</b><br>{exc}")

    def prepare_pretrained_model(self):
        try:
            model_info = self._load_or_train_pretrained_model()
            self.pretrained_model_engine = model_info["model_engine"]
            self.pretrained_data_engine = model_info["data_engine"]
            self.pretrained_model_type = model_info["model_type"]
            self.pretrained_metrics = model_info["metrics"]

            name_map = {"RF": "Random Forest", "GBM": "Gradient Boosting", "MLP": "Neural Network", "TFP": "TFP"}
            model_name = name_map.get(self.pretrained_model_type, self.pretrained_model_type)
            self.pretrained_active_model_info.setText(
                f"사용 중인 모델: {model_name} | 평균 R2 {self.pretrained_metrics['r2_avg']:.3f} | 평균 MAE {self.pretrained_metrics['mae_avg']:.3f}"
            )
            self.pretrained_active_model_info.hide()
            self.pretrained_predict_btn.setEnabled(True)
        except Exception as exc:
            self.pretrained_predict_btn.setEnabled(False)
            self.pretrained_result_display.setText(
                "<b>사전학습 모델을 준비하지 못했습니다.</b><br>"
                f"{exc}"
            )
            self.pretrained_active_model_info.setText("사용 중인 모델: 준비되지 않음")
            self.pretrained_active_model_info.hide()

    def _load_or_train_pretrained_model(self):
        models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"))
        os.makedirs(models_dir, exist_ok=True)

        model_path = os.path.join(models_dir, "pretrained_material_model.pkl")
        data_engine_path = os.path.join(models_dir, "pretrained_data_engine.pkl")
        meta_path = os.path.join(models_dir, "pretrained_material_model_meta.json")
        required_files = {
            "model": model_path,
            "data_engine": data_engine_path,
            "meta": meta_path,
        }
        missing_files = [path for path in required_files.values() if not os.path.exists(path)]
        if missing_files:
            missing_names = ", ".join(os.path.basename(path) for path in missing_files)
            raise FileNotFoundError(
                "사전학습 예측 기능에 필요한 번들 모델 파일이 없습니다: "
                f"{missing_names}"
            )

        pretrained_engine = joblib.load(data_engine_path)
        pretrained_engine.file_path = None
        selected_columns = pretrained_engine.get_selected_training_columns()
        if "Fe" not in selected_columns:
            raise ValueError("사전학습 입력 컬럼 정보가 올바르지 않습니다.")

        pretrained_model = ModelEngine(model_type="RF", output_dim=4)
        pretrained_model.load(model_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        return {
            "model_engine": pretrained_model,
            "data_engine": pretrained_engine,
            "model_type": meta.get("model_type", pretrained_model.model_type),
            "metrics": meta,
        }

    def _quick_save_prediction_csv(self):
        """Ctrl+S: 저장 확인 → 이름 입력 → 분석 기록(워크스페이스)에 저장."""
        state = getattr(self, "_pretrained_prediction_state", None) or \
                getattr(self, "_user_prediction_state", None)
        if not state:
            self.status_label.setText("상태: 저장할 예측 결과가 없습니다")
            return
        reply = QMessageBox.question(
            self, "저장",
            "현재 예측 결과를 분석 기록에 저장하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        default_name = getattr(self, "ws_name_input", None)
        default_name = default_name.text().strip() if default_name else ""
        name, ok = QInputDialog.getText(
            self, "분석 기록 저장", "저장할 이름을 입력하세요:", text=default_name
        )
        if not ok or not name.strip():
            return
        self.ws_name_input.setText(name.strip())
        self.save_workspace()

    def _export_prediction_csv(self, state_attr: str):
        state = getattr(self, state_attr, None)
        if not state:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV로 내보내기", "prediction_result.csv", "CSV 파일 (*.csv)"
        )
        if not path:
            return
        mean = state["mean"]
        std  = state["std"]
        inputs = state["input_dict"]
        targets = [
            ("0.2% 항복강도 (MPa)", mean[0], std[0]),
            ("인장강도 UTS (MPa)",   mean[1], std[1]),
            ("연신율 (%)",           mean[2], std[2]),
            ("단면감소율 (%)",        mean[3], std[3]),
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["=== 입력 조성 / 공정 조건 ==="])
            writer.writerow(["항목", "값"])
            for k, v in inputs.items():
                writer.writerow([k, v])
            writer.writerow([])
            writer.writerow(["=== 예측 결과 ==="])
            writer.writerow(["항목", "예측값", "불확실도 (±)"])
            for label, m, s in targets:
                writer.writerow([label, f"{m:.2f}", f"{s:.2f}"])
            try:
                strain_arr, stress_arr, _pts, _meta, segments = self._build_stress_strain_profile(mean, inputs)
                writer.writerow([])
                writer.writerow(["=== Stress-Strain Curve ==="])
                writer.writerow(["Strain", "Stress (MPa)", "구간"])
                for s, st in zip(*segments["elastic"]):
                    writer.writerow([f"{s:.6f}", f"{st:.4f}", "탄성"])
                hx, hy = segments["hardening"]
                for s, st in zip(hx[1:], hy[1:]):
                    writer.writerow([f"{s:.6f}", f"{st:.4f}", "가공경화"])
                nx, ny = segments["necking"]
                for s, st in zip(nx[1:], ny[1:]):
                    writer.writerow([f"{s:.6f}", f"{st:.4f}", "네킹/파단"])
            except Exception:
                pass

    def update_active_model_display(self):
        name_map = {"RF": "Random Forest", "GBM": "Gradient Boosting", "MLP": "Neural Network", "TFP": "TFP"}
        self.active_model_info.setText(f"현재 예측 모델: {name_map.get(self.model_type, self.model_type)}")
        if self.pretrained_model_type and hasattr(self, "pretrained_active_model_info"):
            metrics = self.pretrained_metrics or {}
            model_name = name_map.get(self.pretrained_model_type, self.pretrained_model_type)
            if metrics:
                self.pretrained_active_model_info.setText(
                    f"사용 중인 모델: {model_name} | 평균 R2 {metrics.get('r2_avg', 0):.3f} | 평균 MAE {metrics.get('mae_avg', 0):.3f}"
                )
            else:
                self.pretrained_active_model_info.setText(f"사용 중인 모델: {model_name}")
        self._apply_theme_colors()
