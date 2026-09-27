import os

import html as _html

from PyQt6.QtCore import QPoint, QRectF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from src.gui.widgets.floating_chatbot import RobotAvatarWidget
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizeGrip,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

class _ChatHeader(QWidget):
    """드래그로 창 이동 + 헤더 UI (화이트 스타일)."""
    clear_requested = pyqtSignal()

    def __init__(self, dialog):
        super().__init__(dialog)
        self._dialog = dialog
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(58)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setStyleSheet("background:white;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(8)

        # 아바타
        av = RobotAvatarWidget(size=38)
        layout.addWidget(av)

        # 타이틀
        col = QVBoxLayout()
        col.setSpacing(1)
        t1 = QLabel("AI 재료 문의")
        t1.setStyleSheet("color:#111827;font-size:13px;font-weight:700;background:transparent;")
        t2 = QLabel("오스테나이트 스테인리스강 전문")
        t2.setStyleSheet("color:#6B7280;font-size:10px;background:transparent;")
        col.addWidget(t1)
        col.addWidget(t2)
        layout.addLayout(col)
        layout.addStretch()

        # 예측 포함 체크박스 — 기본 스타일 유지, 텍스트 색만 지정
        self.ctx_cb = QCheckBox("현재 분석 포함")
        self.ctx_cb.setChecked(True)
        self.ctx_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ctx_cb.setStyleSheet(
            "QCheckBox{color:#6B7280;font-size:10px;background:transparent;spacing:4px;}"
        )
        layout.addWidget(self.ctx_cb)
        # graph_cb는 ctx_cb와 병합 — 체크 시 예측 수치 + 그래프 이미지 모두 전송
        self.graph_cb = self.ctx_cb

        # 초기화
        clear_btn = QPushButton("↺ 초기화")
        clear_btn.setFixedHeight(28)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setToolTip("대화 초기화")
        clear_btn.setStyleSheet(
            "QPushButton{background:#3B82F6;color:white;border:none;"
            "font-size:11px;font-weight:700;border-radius:6px;padding:0 10px;}"
            "QPushButton:hover{background:#1E293B;}"
        )
        clear_btn.clicked.connect(self.clear_requested)
        layout.addWidget(clear_btn)

        # 닫기 — Windows 타이틀바 스타일
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(46, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("닫기")
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#6B7280;border:none;"
            "font-size:11px;font-weight:600;border-radius:4px;}"
            "QPushButton:hover{background:#EF4444;color:white;}"
        )
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 흰 배경 + 둥근 상단
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height() + 20), 20, 20)
        p.fillPath(path, QColor("white"))
        # 하단 구분선
        p.setPen(QColor("#F0F0F0"))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def _on_close(self):
        """닫기 버튼 — 대화 초기화 플래그만 설정 후 숨김."""
        self._dialog._messages.clear()
        self._dialog._chat_display.clear()
        self._dialog._pending_welcome = True
        self._dialog.hide()


# ── 오스테나이트계 스테인리스강 전문 시스템 프롬프트 ─────────────────────────
_SYSTEM_PROMPT = """
당신은 오스테나이트계 스테인리스강 전문 재료공학자이자 이 AI 예측 플랫폼의 전문 보조 시스템입니다.

## 이 플랫폼 정보
오스테나이트계 스테인리스강의 4가지 기계적 물성을 화학 조성·공정 조건으로 예측합니다.
- 예측 물성: 0.2% 항복강도(MPa), 인장강도 UTS(MPa), 연신율(%), 단면감소율(%)
- 앙상블 모델: RF(Random Forest), GBM(Gradient Boosting), MLP(신경망), TFP(불확실성 정량화)
- 엔지니어드 피처: Ni_eq, Cr_eq, Cr/Ni 비율, C+N

## 합금 성분별 역할
- Cr (16~26%): 내식성 핵심. Cr_eq = Cr + Mo + 1.5Si + 0.5Nb
- Ni (6~22%): 오스테나이트 안정화, 연성·인성 향상. Ni_eq = Ni + 30C + 0.5Mn + 30N + 0.3Cu
- Mo (0~3%): 공식 저항성, 고온 크리프 강도
- N (0~0.5%): 강력한 고용강화 (C의 ~30배). 입계 예민화 억제
- C (0~0.15%): 고용강화, 과다 시 Cr₂₃C₆ 석출 → 예민화 위험
- Mn (0~2%): 오스테나이트 안정화, N 고용도 증가
- Si (0~1%): 산화 저항성, 내산성
- Nb, Ti: 탄질화물 형성으로 예민화 억제

## 주요 강종
- AISI 304 (18Cr-8Ni): 범용, YS 205~310 MPa, UTS 515~620 MPa
- AISI 316 (16Cr-10Ni-2Mo): 내식성↑
- AISI 310 (25Cr-20Ni): 고온 내열용
- AISI 321 (Ti 안정화), AISI 347 (Nb 안정화): 예민화 저항

## 열처리
- 고용화 처리: 1010~1150°C → 급냉 (오스테나이트 단상화, 탄화물 재용해)
- 예민화: 425~870°C 장시간 → Cr₂₃C₆ 입계 석출 → 내식성 저하
- 응력제거 풀림: 850~950°C

## Schaeffler 선도
- Cr_eq = Cr + Mo + 1.5Si + 0.5Nb
- Ni_eq = Ni + 30C + 0.5Mn + 30N + 0.3Cu

## 답변 원칙
1. 반드시 한국어(한글)로만 답변하세요. 한자·일본어 절대 사용 금지.
2. 전문 용어는 영어 원어 유지, 나머지는 한글.
3. 수치·수식 근거 포함 (MPa, wt% 등 단위 명기)
4. 예측 결과가 제공되면 해당 합금을 구체적으로 분석
5. 실용적 조언 우선 (설계 개선안, 공정 조정 방향)
""".strip()

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL_DEFAULT = "gpt-4o-mini"


class _OpenAIWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key: str, model: str, messages: list, system_prompt: str):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.messages = messages
        self.system_prompt = system_prompt

    def run(self):
        try:
            import requests  # noqa: PLC0415
            resp = requests.post(
                _OPENAI_URL,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": self.system_prompt}] + self.messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
                timeout=60,
            )
            data = resp.json()
            if resp.status_code != 200 or "error" in data:
                err = data.get("error", {})
                self.error_occurred.emit(f"OpenAI 오류 [{err.get('code', resp.status_code)}]: {err.get('message', resp.text)}")
                return
            self.response_received.emit(data["choices"][0]["message"]["content"])
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(f"오류: {exc}")


_SHADOW = 10  # 그림자 여백

class FloatingChatDialog(QDialog):
    """모바일 앱 스타일 AI 문의 채팅 창."""

    def __init__(self, context_fn, graph_fn=None, parent=None):
        super().__init__(parent)
        self._context_fn = context_fn
        self._graph_fn = graph_fn
        self._messages: list[dict] = []
        self._worker: _OpenAIWorker | None = None
        self._drag_pos: QPoint | None = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(380 + _SHADOW * 2, 600 + _SHADOW * 2)
        self.setMinimumSize(300 + _SHADOW * 2, 420 + _SHADOW * 2)
        self._build_ui()

    # ── 배경 (둥근 모서리 + 그림자) ───────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._send()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        if not p.isActive():
            return
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            s = _SHADOW
            w, h = self.width(), self.height()
            if w <= s * 2 or h <= s * 2:
                return
            rect = QRectF(s, s, w - s * 2, h - s * 2)

            # 그림자
            for i in range(s, 0, -1):
                p.setBrush(QColor(0, 0, 0, max(2, 22 - i * 2)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect.adjusted(-i * 0.4, -i * 0.4, i * 0.4, i * 0.4), 20, 20)

            # 창 배경 (흰색)
            p.setBrush(QColor(255, 255, 255))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, 20, 20)
        except Exception:
            pass
        finally:
            p.end()

    def _build_ui(self):
        s = _SHADOW
        layout = QVBoxLayout(self)
        layout.setContentsMargins(s, s, s, s)
        layout.setSpacing(0)

        # ── 헤더 ──────────────────────────────────────────────────────────────
        self._header = _ChatHeader(self)
        self._header.clear_requested.connect(self._clear)
        self._ctx_cb = self._header.ctx_cb
        self._graph_cb = self._header.graph_cb
        layout.addWidget(self._header)

        # ── 채팅 표시 (QTextEdit HTML) ────────────────────────────────────────
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setStyleSheet(
            "QTextEdit{background:#F7F8FA;padding:8px;border:none;font-size:12px;}"
        )
        self._chat_display.document().setDefaultStyleSheet(
            "body{font-family:'Malgun Gothic',sans-serif;font-size:12px;}"
        )
        layout.addWidget(self._chat_display, 1)

        self._pending_welcome = False
        self._add_welcome()   # 최초 1회 웰컴 메시지

        # ── 입력 영역 ──────────────────────────────────────────────────────────
        input_bar = QWidget()
        input_bar.setFixedHeight(62)
        input_bar.setStyleSheet(
            "background:white;border-top:1px solid #F0F0F0;"
            "border-bottom-left-radius:20px;border-bottom-right-radius:20px;"
        )
        irow = QHBoxLayout(input_bar)
        irow.setContentsMargins(14, 10, 10, 10)
        irow.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("질문을 입력하세요...")
        self._input.setFixedHeight(38)
        self._input.returnPressed.connect(self._send)
        self._input.setStyleSheet(
            "QLineEdit{background:#F3F4F6;border:none;border-radius:19px;"
            "padding:0 14px;font-size:12px;color:#111827;}"
            "QLineEdit:focus{background:#EEF2FF;outline:none;}"
        )
        irow.addWidget(self._input, 1)

        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(38, 38)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(
            "QPushButton{background:#3B82F6;color:white;border:none;"
            "border-radius:19px;font-size:13px;}"
            "QPushButton:hover{background:#1E293B;}"
            "QPushButton:disabled{background:#D1D5DB;}"
        )
        self._send_btn.clicked.connect(self._send)
        irow.addWidget(self._send_btn)

        grip = QSizeGrip(input_bar)
        grip.setFixedSize(14, 14)
        irow.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(input_bar)

        # 숨김 위젯
        self._model_edit = QLineEdit()
        self._model_edit.setText(_OPENAI_MODEL_DEFAULT)
        self._model_edit.hide()
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setText(os.environ.get("OPENAI_API_KEY", ""))
        self._api_key_edit.hide()


    def _add_welcome(self):
        self._add_bubble(
            "안녕하세요! 오스테나이트계 스테인리스강 전문 AI입니다.\n"
            "합금 조성·기계적 물성·열처리 공정에 대해 질문해 주세요.",
            is_user=False,
        )

    # ── 메시지 전송 ────────────────────────────────────────────────────────────

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return

        # 질문 버블을 먼저 표시
        self._input.clear()
        self._add_bubble(text, is_user=True)

        api_key = self._api_key_edit.text().strip() or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self._add_bubble("API 키가 없습니다. .env 파일에 OPENAI_API_KEY를 설정해 주세요.", is_user=False)
            return

        if not api_key.startswith("sk-") or len(api_key) < 20:
            self._add_bubble("API 키 형식이 올바르지 않습니다 (sk-... 형식).", is_user=False)
            self._api_key_edit.clear()
            return
        self._send_btn.setEnabled(False)
        self._send_btn.setText("…")

        system_prompt = _SYSTEM_PROMPT
        if self._ctx_cb.isChecked():
            ctx = self._context_fn()
            if ctx:
                system_prompt += f"\n\n--- 현재 예측 결과 ---\n{ctx}"

        # 그래프 이미지 캡처 (선택 시)
        graph_images: list[str] = []
        if self._graph_cb.isChecked() and self._graph_fn:
            graph_images = self._graph_fn()

        if graph_images:
            # 비전 API 형식 (text + images)
            content: list | str = [{"type": "text", "text": text}]
            for b64 in graph_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"},
                })
            self._messages.append({"role": "user", "content": content})
        else:
            self._messages.append({"role": "user", "content": text})

        model = self._model_edit.text().strip() or _OPENAI_MODEL_DEFAULT

        self._worker = _OpenAIWorker(api_key, model, list(self._messages), system_prompt)
        self._worker.response_received.connect(self._on_response)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_response(self, text: str):
        self._messages.append({"role": "assistant", "content": text})
        self._add_bubble(text, is_user=False)
        self._send_btn.setEnabled(True)
        self._send_btn.setText("➤")

    def _on_error(self, text: str):
        self._add_bubble(f"[오류] {text}", is_user=False)
        self._send_btn.setEnabled(True)
        self._send_btn.setText("➤")

    def _clear(self):
        self._messages = []
        self._chat_display.clear()

        self._add_bubble(
            "안녕하세요! 오스테나이트계 스테인리스강 전문 AI입니다.\n"
            "합금 조성·기계적 물성·열처리 공정에 대해 질문해 주세요.",
            is_user=False,
        )

    # ── 버블 (HTML) ───────────────────────────────────────────────────────────

    def _add_bubble(self, text: str, *, is_user: bool):
        from PyQt6.QtGui import QTextCursor  # noqa: PLC0415

        escaped = _html.escape(text).replace("\n", "<br>")
        if is_user:
            part = (
                '<table width="100%" cellspacing="4" cellpadding="0"><tr>'
                '<td width="15%">&nbsp;</td>'
                '<td align="right" width="85%">'
                f'<table cellpadding="10" cellspacing="0" bgcolor="#3B82F6"><tr>'
                f'<td><font color="#FFFFFF">{escaped}</font></td>'
                '</tr></table>'
                '</td></tr></table>'
            )
        else:
            part = (
                '<table width="100%" cellspacing="4" cellpadding="0"><tr>'
                '<td align="left" width="85%">'
                f'<table cellpadding="10" cellspacing="0" bgcolor="#EBEBEB"><tr>'
                f'<td><font color="#111827">{escaped}</font></td>'
                '</tr></table>'
                '</td>'
                '<td width="15%">&nbsp;</td>'
                '</tr></table>'
            )

        # document 레벨 커서로 직접 삽입 — setReadOnly 제약 없이 항상 작동
        cursor = QTextCursor(self._chat_display.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(part)
        self._chat_display.setTextCursor(cursor)
        self._chat_display.ensureCursorVisible()


class LLMChatMixin:
    """FloatingChatDialog 생성 및 토글."""

    def _llm_build_context(self) -> str:
        PROP_NAMES = ["항복강도(MPa)", "UTS(MPa)", "연신율(%)", "단면감소율(%)"]
        for attr, label in (
            ("_pretrained_prediction_state", "사전학습 모델"),
            ("_user_prediction_state", "사용자 학습 모델"),
        ):
            state = getattr(self, attr, None)
            if state is None:
                continue
            mean, std, inp = state.get("mean"), state.get("std"), state.get("input_dict", {})
            if mean is None:
                continue
            lines = [f"[{label} 예측 결과]"]
            for name, m, s in zip(PROP_NAMES, mean, std):
                lines.append(f"  {name}: {float(m):.1f} ± {float(s):.1f}")
            if inp:
                lines.append("[입력 조성 / 공정]")
                lines.extend(f"  {k}: {v}" for k, v in list(inp.items())[:16])
            return "\n".join(lines)
        return ""

    def _capture_graphs(self) -> list[str]:
        """현재 화면의 그래프 위젯을 캡처해 base64 PNG 리스트로 반환."""
        import base64  # noqa: PLC0415
        from PyQt6.QtCore import QBuffer, QByteArray, QIODeviceBase  # noqa: PLC0415

        result = []
        for attr in ["pretrained_curve_canvas", "pretrained_prediction_canvas",
                     "stress_strain_canvas", "prediction_canvas"]:
            widget = getattr(self, attr, None)
            if widget is None:
                continue
            try:
                pixmap = widget.grab()
                if pixmap.isNull():
                    continue
                ba = QByteArray()
                buf = QBuffer(ba)
                buf.open(QIODeviceBase.OpenModeFlag.WriteOnly)
                pixmap.save(buf, "PNG")
                buf.close()
                result.append(base64.b64encode(ba.data()).decode())
            except Exception:  # noqa: BLE001
                pass
        return result

    def toggle_llm_chat_dialog(self):
        if not hasattr(self, "_llm_dialog") or self._llm_dialog is None:
            self._llm_dialog = FloatingChatDialog(
                context_fn=self._llm_build_context,
                graph_fn=self._capture_graphs,
                parent=self,
            )
        if self._llm_dialog.isVisible():
            self._llm_dialog.hide()
        else:
            # X로 닫혔던 경우 → show 직전에 딱 한 번 웰컴 추가
            if getattr(self._llm_dialog, "_pending_welcome", False):
                self._llm_dialog._pending_welcome = False
                self._llm_dialog._add_welcome()
            self._llm_dialog.show()
            self._llm_dialog.raise_()
            self._llm_dialog.activateWindow()
            self._llm_dialog._input.setFocus()

    def _apply_llm_chat_theme(self):
        pass  # 다이얼로그는 별도 OS 창이므로 테마 연동 불필요
