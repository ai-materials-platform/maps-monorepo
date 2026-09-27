import matplotlib.pyplot as plt
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QMainWindow

from src.engine.data_engine import DataEngine
from src.gui.constants import APP_FONT_SIZE
from src.gui.mixins import (
    ChartsMixin,
    FeatureSelectionMixin,
    InferenceMixin,
    LLMChatMixin,
    PreprocessingMixin,
    ProcessConditionMixin,
    SettingsPanelMixin,
    ThemeMixin,
    TrainingMixin,
    UISetupMixin,
    WorkspaceMixin,
)

try:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


class MainWindow(
    QMainWindow,
    UISetupMixin,
    ThemeMixin,
    SettingsPanelMixin,
    PreprocessingMixin,
    FeatureSelectionMixin,
    TrainingMixin,
    InferenceMixin,
    ChartsMixin,
    WorkspaceMixin,
    ProcessConditionMixin,
    LLMChatMixin,
):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAPS — Microstructure & Alloy Prediction System")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        from PyQt6.QtGui import QIcon  # noqa: PLC0415
        import pathlib
        _icon_path = pathlib.Path(__file__).parents[2] / "assets" / "icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))
        else:
            from src.gui.widgets.maps_logo import MAPSLogoWidget  # noqa: PLC0415
            self.setWindowIcon(MAPSLogoWidget.as_icon(64))
        screen = QApplication.primaryScreen().availableGeometry()
        init_w = min(1400, max(960, int(screen.width() * 0.88)))
        init_h = min(900, max(680, int(screen.height() * 0.88)))
        self.resize(init_w, init_h)
        self.setMinimumSize(900, 650)

        self.data_engine = DataEngine(None)
        self.model_engine = None
        self.model_type = "RF"
        self.pretrained_model_engine = None
        self.pretrained_data_engine = None
        self.pretrained_model_type = None
        self.pretrained_metrics = None
        self.preprocessing_ready = False
        self._open_dialogs = []
        self.last_r2_avg = None
        self._ui_font_family = "Malgun Gothic"
        self._ui_font_size = APP_FONT_SIZE
        self._dark_mode = False
        self._panel_widgets = []
        self._panel_header_widgets = []
        self._divider_widgets = []
        self._info_box_widgets = []
        self._section_lbl_widgets = []
        self._muted_bg_widgets = []
        self._prediction_input_groups = []
        self._prediction_input_fields = []
        self._prediction_input_labels = []
        self._curve_info_panels = []
        self._curve_legend_cards = []
        self._curve_legend_label_widgets = []
        self._simulation_status_labels = []
        self._simulation_detail_labels = []
        self._simulation_assumption_labels = []
        self._simulation_control_cards = []
        self._simulation_reset_buttons = []
        self._simulation_widgets = []
        self._pretrained_prediction_state = None
        self._user_prediction_state = None

        self.init_ui()

        _sc = QShortcut(QKeySequence("Ctrl+S"), self)
        _sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        _sc.activated.connect(self._quick_save_prediction_csv)

    # ── 가장자리 리사이즈 (nativeEvent 대신 Qt 네이티브 API 사용) ──────────────

    def _resize_edge(self, global_pos):
        """global_pos 가 리사이즈 존에 있으면 Qt.Edge 반환, 없으면 None."""
        geo = self.frameGeometry()
        b = 6
        nav_h = 80  # 타이틀바+툴바 — 이 영역 상단/좌우 리사이즈 제외

        x, y = global_pos.x(), global_pos.y()
        on_l = x < geo.left()   + b
        on_r = x > geo.right()  - b
        on_t = y < geo.top()    + b
        on_b = y > geo.bottom() - b
        in_nav = y < geo.top() + nav_h
        in_win_btns = (y < geo.top() + 30) and (x > geo.right() - 140)

        edge = Qt.Edge(0)
        if on_l and not in_nav:              edge |= Qt.Edge.LeftEdge
        if on_r and not in_nav and not in_win_btns: edge |= Qt.Edge.RightEdge
        if on_t and not in_nav and not in_win_btns: edge |= Qt.Edge.TopEdge
        if on_b:                             edge |= Qt.Edge.BottomEdge
        return edge if edge else None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._resize_edge(event.globalPosition().toPoint())
            if edge and self.windowHandle():
                self.windowHandle().startSystemResize(edge)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        edge = self._resize_edge(event.globalPosition().toPoint())
        if edge:
            v = bool(edge & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
            h = bool(edge & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
            if v and h:
                is_tl = bool(edge & Qt.Edge.TopEdge) and bool(edge & Qt.Edge.LeftEdge)
                self.setCursor(Qt.CursorShape.SizeFDiagCursor if is_tl else Qt.CursorShape.SizeBDiagCursor)
            elif v:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)
