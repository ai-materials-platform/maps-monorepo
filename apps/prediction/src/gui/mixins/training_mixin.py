import os

import numpy as np

from src.gui.threads import TrainingThread


class TrainingMixin:
    def on_train_clicked(self):
        if not self.data_engine.file_path or not os.path.exists(self.data_engine.file_path):
            self.training_status_label.setText("상태: 오류 - 먼저 데이터 파일을 선택해 주세요.")
            return

        if not self.preprocessing_ready:
            self.training_status_label.setText("상태: 1번 탭에서 전처리를 먼저 실행해 주세요.")
            return

        selected_columns = self.data_engine.get_selected_training_columns(default_to_all=False)
        if not selected_columns:
            self.training_status_label.setText("상태: 오류 - 학습할 컬럼을 하나 이상 선택해 주세요.")
            self.tabs.setCurrentIndex(1)
            return

        self.apply_quality_settings_from_ui()
        self.train_btn.setEnabled(False)
        self.training_status_label.setText(
            f"상태: 학습 준비 중입니다. 선택한 컬럼 {len(selected_columns)}개만 사용합니다."
        )
        self.metrics_label.setText("<b>모델 성능 요약:</b><br>- 계산 중...")

        model_map = {0: "RF", 1: "GBM", 2: "MLP", 3: "TFP"}
        self.model_type = model_map.get(self.model_combo.currentIndex(), "RF")

        self.thread = TrainingThread(self.data_engine, model_type=self.model_type, max_iter=self.iter_spin.value())
        self.thread.progress.connect(lambda text: self.training_status_label.setText(f"상태: {text}"))
        self.thread.finished.connect(self.on_training_finished)
        self.thread.start()

    def on_training_finished(self, results):
        self.train_btn.setEnabled(True)
        if isinstance(results, str):
            self.training_status_label.setText(f"상태: 오류 발생 - {results}")
            return

        self.model_engine = results["model"]
        self.training_status_label.setText(f"상태: {self.model_type} 모델 학습이 완료되었습니다.")
        self.update_active_model_display()
        self.update_quality_summary_from_report(results.get("quality_report", {}))

        metrics = results["metrics"]
        r2_avg = float(np.mean(metrics["r2"]))
        mae_avg = float(np.mean(metrics["mae"]))
        self.last_r2_avg = round(r2_avg, 4)
        self._last_metrics = metrics
        self._last_training_results = results
        acc_text = "매우 높음" if r2_avg > 0.9 else "높음" if r2_avg > 0.8 else "보통"

        self.metrics_label.setText(
            f"<b>종합 모델 성능 요약:</b><br>- 평균 예측 정확도(R2): <b>{r2_avg * 100:.1f}% ({acc_text})</b><br>- 평균 오차(MAE): <b>{mae_avg:.2f}</b>"
        )

        self._render_training_bar_chart(metrics)
        self.render_performance_results(results)

        self.auto_save_workspace()
        self._update_project_tree()
        self._sb_status.setText("● 학습 완료")
        self._sb_status.setStyleSheet("color: #58C472; font-size: 11px; font-weight: 700; padding: 0 10px;")

        self.append_log({
            "type": "학습",
            "model": self.model_type,
            "data_file": os.path.basename(self.data_engine.file_path or ""),
            "r2_avg": round(float(np.mean(metrics["r2"])), 4),
            "mae_avg": round(float(np.mean(metrics["mae"])), 4),
            "r2_per_target": [round(float(v), 4) for v in metrics["r2"]],
            "mae_per_target": [round(float(v), 4) for v in metrics["mae"]],
        })

    def _render_training_bar_chart(self, metrics):
        c = self._theme()
        bg = c["panel_bg"]
        text_main = c["text_primary"]
        text_sec = c["text_sec"]
        border = c["border"]

        self.canvas.axes.clear()
        self.canvas.axes.set_facecolor(bg)
        self.canvas.fig.patch.set_facecolor(bg)

        target_names = ["Yield Stress", "UTS", "Elongation", "Area Red."]
        r2_scores = metrics["r2"]
        bar_colors = ["#3498db" if s > 0.8 else "#f1c40f" if s > 0.6 else "#e74c3c" for s in r2_scores]
        bars = self.canvas.axes.bar(target_names, r2_scores, color=bar_colors)
        self.canvas.axes.set_ylim(0, 1.1)
        self.canvas.axes.set_ylabel("정확도 (R2 Score)", color=text_sec, fontsize=9)
        for bar in bars:
            height = bar.get_height()
            self.canvas.axes.text(
                bar.get_x() + bar.get_width() / 2.0, height + 0.02, f"{height:.2f}",
                ha="center", va="bottom", fontsize=9, color=text_main,
            )
        name_map = {"RF": "Random Forest", "GBM": "Gradient Boosting", "MLP": "Neural Network", "TFP": "TFP"}
        self.canvas.axes.set_title(
            f"모델별 특성 예측 정확도 ({name_map.get(self.model_type, self.model_type)})",
            color=text_main, fontsize=10,
        )
        for spine in self.canvas.axes.spines.values():
            spine.set_color(border)
        self.canvas.axes.tick_params(axis="both", colors=text_sec, labelcolor=text_sec)
        self.canvas.draw()

    def render_performance_results(self, results):
        c = self._theme()
        bg = c["panel_bg"]
        text_main = c["text_primary"]
        text_sec = c["text_sec"]
        border = c["border"]
        divider = c["divider"]

        self.perf_canvas.figure.clear()
        self.perf_canvas.figure.patch.set_facecolor(bg)
        axes = self.perf_canvas.figure.subplots(2, 2)
        y_test = results["y_test"].values
        y_pred = results["y_pred"]
        target_names = ["Yield Stress (MPa)", "UTS (MPa)", "Elongation (%)", "Area Reduction (%)"]
        scatter_colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"]

        for index, ax in enumerate(axes.flatten()):
            ax.set_facecolor(bg)
            x_data = y_test[:, index]
            y_data = y_pred[:, index]
            all_data = np.concatenate([x_data, y_data])
            min_val, max_val = all_data.min(), all_data.max()

            # 밀도 등고선
            try:
                from scipy.stats import gaussian_kde
                if len(x_data) >= 12:
                    xi = np.linspace(min_val, max_val, 48)
                    Xi, Yi = np.meshgrid(xi, xi)
                    kde = gaussian_kde(np.vstack([x_data, y_data]))
                    Zi = kde(np.vstack([Xi.ravel(), Yi.ravel()])).reshape(48, 48)
                    ax.contourf(Xi, Yi, Zi, levels=10, cmap="Blues" if bg == "#FFFFFF" else "Blues",
                                alpha=0.22, zorder=1)
                    ax.contour(Xi, Yi, Zi, levels=5, colors=[scatter_colors[index]],
                               alpha=0.45, linewidths=0.7, zorder=2)
            except Exception:
                pass

            ax.scatter(x_data, y_data, alpha=0.60, color=scatter_colors[index], s=16, zorder=3)
            ax.plot([min_val, max_val], [min_val, max_val], "--", color=divider, alpha=0.8, lw=1, zorder=4)
            ax.set_title(target_names[index], fontsize=10, fontweight="bold", color=text_main)
            ax.set_xlabel("실제값", fontsize=9, color=text_sec)
            ax.set_ylabel("예측값", fontsize=9, color=text_sec)
            ax.grid(True, linestyle=":", alpha=0.4, color=divider)
            for spine in ax.spines.values():
                spine.set_color(border)
            ax.tick_params(axis="both", colors=text_sec, labelcolor=text_sec)

        self.perf_canvas.figure.tight_layout(pad=0.4)
        self.perf_canvas.draw()
