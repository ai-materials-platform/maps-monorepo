APP_FONT_FAMILY = '"Malgun Gothic"'
APP_FONT_SIZE = 11

# 색·글꼴은 apps/shared/maps-theme.css(세 앱 공통)에서 온다. 여기엔 Qt 위젯별 배치만 둔다.
# 토큰에 없는 보조 색(눌림·스크롤바 등)은 템플릿에 그대로 둔다.
_LIGHT_TEMPLATE = """
QMainWindow, QWidget {{ background-color: {bg}; color: {text}; font-family: {font}; font-size: {size}px; }}
QTabWidget::pane {{ border: 1px solid {border}; background: {panel}; }}
QTabBar {{ background: #E9EEF3; }}
QTabBar::tab {{ background: #E9EEF3; color: {text_secondary}; padding: 9px 16px; border: 1px solid {border}; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:selected {{ background: {panel}; color: {text}; font-weight: 700; border-bottom: 2px solid {accent}; }}
QTabBar::tab:hover {{ background: {panel}; color: {text}; }}
QGroupBox {{ border: 1px solid {border}; border-radius: 10px; margin-top: 12px; padding-top: 12px; font-weight: 700; color: #28323C; background: {panel}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {text_secondary}; letter-spacing: 0.3px; }}
QPushButton {{ background-color: #EEF2F6; color: {text}; border: 1px solid {border}; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background-color: #E2E8F0; }}
QPushButton:disabled {{ color: #7C8794; background: #F4F5F6; border-color: #E2E7EC; }}
QComboBox {{ border: 1px solid {border}; border-radius: 8px; background: {panel}; padding: 6px 10px; color: {text}; }}
QComboBox:focus {{ border-color: {accent}; }}
QComboBox QAbstractItemView {{ background: {panel}; border: 1px solid {border}; color: {text}; selection-background-color: {accent}; selection-color: {panel}; }}
QTableWidget {{ border: 1px solid {border}; gridline-color: #E2E8F0; background: {panel}; alternate-background-color: {panel_muted}; color: {text}; }}
QTableWidget::item {{ background-color: {panel}; color: {text}; }}
QTableWidget::item:alternate {{ background-color: {panel_muted}; }}
QTableWidget::item:selected {{ background: {accent}; color: {panel}; }}
QHeaderView::section {{ background: #E9EEF3; color: {text_secondary}; border: none; border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: 7px 10px; font-weight: 700; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #B8C2CE; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #B8C2CE; border-radius: 4px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit {{ border: 1px solid {border}; border-radius: 8px; background: {panel}; padding: 7px 10px; color: {text}; selection-background-color: {accent}; }}
QLineEdit:focus {{ border-color: {accent}; }}
QDoubleSpinBox, QSpinBox {{ border: 1px solid {border}; border-radius: 8px; background: {panel}; padding: 7px 10px; color: {text}; }}
QSplitter::handle {{ background: {border}; }}
QDialog {{ background: {panel}; }}
QMessageBox {{ background: {panel}; }}
QToolTip {{ background: #FFFFE1; color: {text}; border: 1px solid #767676; border-radius: 0px; padding: 5px 10px; font-size: 11px; }}
QMenu {{ background: {panel}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; background: transparent; }}
QMenu::item:selected {{ background: {menu_hover}; }}
QMenu::item:disabled {{ color: {text_muted}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0; }}
"""

_DARK_TEMPLATE = """
QMainWindow, QWidget {{ background-color: {bg}; color: {text}; font-family: {font}; font-size: {size}px; }}
QTabWidget {{ background: {bg}; }}
QTabWidget::pane {{ border: 1px solid {border}; background: {panel}; }}
QTabBar {{ background: {bg}; }}
QTabBar::scroller {{ background: {bg}; }}
QTabBar QToolButton {{ background: {bg}; border: none; }}
QTabBar::tab {{ background: {bg}; color: {text_muted}; padding: 8px 16px; border: 1px solid {border}; border-bottom: none; border-top-left-radius: 3px; border-top-right-radius: 3px; }}
QTabBar::tab:selected {{ background: {panel}; color: #FFFFFF; font-weight: 700; border-bottom: 2px solid #5B8DEF; }}
QTabBar::tab:hover {{ background: {panel_muted}; color: {text}; }}
QGroupBox {{ border: 1px solid {border}; border-radius: 3px; margin-top: 16px; padding-top: 14px; font-weight: 700; color: {text}; background: {panel}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 6px; color: {text_muted}; font-size: 11px; letter-spacing: 0.2px; }}
QPushButton {{ background-color: {panel_muted}; color: {text}; border: 1px solid {border}; border-radius: 3px; padding: 5px 12px; }}
QPushButton:hover {{ background-color: #3A3A3A; color: #FFFFFF; border-color: #5A5A5A; }}
QPushButton:disabled {{ color: #5A5A5A; background: {bg}; border-color: {border}; }}
QComboBox {{ border: 1px solid {border}; border-radius: 3px; background: {panel}; padding: 5px 10px; color: {text}; }}
QComboBox:focus {{ border-color: #5B8DEF; }}
QComboBox QAbstractItemView {{ background: {panel}; border: 1px solid {border}; color: {text}; selection-background-color: {panel_muted}; selection-color: #FFFFFF; }}
QTableWidget {{ border: 1px solid {border}; gridline-color: {panel_muted}; background: {panel}; alternate-background-color: {bg}; color: {text}; }}
QTableWidget::item {{ background-color: {panel}; color: {text}; }}
QTableWidget::item:alternate {{ background-color: {bg}; }}
QTableWidget::item:selected {{ background: #3A4A6B; color: #FFFFFF; }}
QHeaderView::section {{ background: {bg}; color: {text_muted}; border: none; border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: 6px 10px; font-weight: 700; }}
QScrollBar:vertical {{ width: 7px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #5A5A5A; border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 7px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #5A5A5A; border-radius: 3px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit {{ border: 1px solid {border}; border-radius: 3px; background: #3C3C3C; padding: 5px 10px; color: {text}; selection-background-color: #3A4A6B; }}
QLineEdit:focus {{ border-color: #5B8DEF; }}
QDoubleSpinBox, QSpinBox {{ border: 1px solid {border}; border-radius: 3px; background: #3C3C3C; padding: 5px 10px; color: {text}; }}
QSplitter::handle {{ background: {border}; }}
QDialog {{ background: {panel}; color: {text}; }}
QMessageBox {{ background: {panel}; color: {text}; }}
QScrollArea {{ background: transparent; border: none; }}
QToolTip {{ background: {panel}; color: {text}; border: 1px solid {border}; border-radius: 3px; padding: 5px 10px; font-size: 11px; }}
QMenu {{ background: {panel}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; background: transparent; }}
QMenu::item:selected {{ background: {menu_hover}; }}
QMenu::item:disabled {{ color: {text_muted}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0; }}
"""

_TOKEN_KEYS = ("bg", "panel", "panel-muted", "border", "text", "text-secondary", "text-muted", "accent", "menu-hover")


def build_qss(dark: bool) -> str:
    from src.gui.theme_tokens import token

    values = {k.replace("-", "_"): token(f"maps-{k}", dark) for k in _TOKEN_KEYS}
    return (_DARK_TEMPLATE if dark else _LIGHT_TEMPLATE).format(
        font=token("maps-font-sans", dark), size=APP_FONT_SIZE, **values)


CURVE_SEGMENT_STYLES = {
    "elastic": {
        "color": "#2563EB",
        "fill": "#93C5FD",
        "label": "Elastic region",
        "legend_html": '<span style="color:#2563EB; font-weight:700;">파란색</span> = Elastic region',
    },
    "hardening": {
        "color": "#F59E0B",
        "fill": "#FCD34D",
        "label": "Plastic hardening",
        "legend_html": '<span style="color:#F59E0B; font-weight:700;">주황색</span> = Plastic hardening',
    },
    "necking": {
        "color": "#DC2626",
        "fill": "#FCA5A5",
        "label": "Necking",
        "legend_html": '<span style="color:#DC2626; font-weight:700;">빨간색</span> = Necking',
    },
}
