APP_FONT_FAMILY = '"Malgun Gothic"'
APP_FONT_SIZE = 11

LIGHT_QSS = f"""
QMainWindow, QWidget {{ background-color: #F4F6F8; color: #111827; font-family: {APP_FONT_FAMILY}; font-size: {APP_FONT_SIZE}px; }}
QTabWidget::pane {{ border: 1px solid #C9D2DC; background: #FFFFFF; }}
QTabBar {{ background: #E9EEF3; }}
QTabBar::tab {{ background: #E9EEF3; color: #475569; padding: 9px 16px; border: 1px solid #C9D2DC; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:selected {{ background: #FFFFFF; color: #111827; font-weight: 700; border-bottom: 2px solid #1E293B; }}
QTabBar::tab:hover {{ background: #FFFFFF; color: #111827; }}
QGroupBox {{ border: 1px solid #C9D2DC; border-radius: 10px; margin-top: 12px; padding-top: 12px; font-weight: 700; color: #28323C; background: #FFFFFF; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #475569; letter-spacing: 0.3px; }}
QPushButton {{ background-color: #EEF2F6; color: #111827; border: 1px solid #C9D2DC; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ background-color: #E2E8F0; }}
QPushButton:disabled {{ color: #7C8794; background: #F4F5F6; border-color: #E2E7EC; }}
QComboBox {{ border: 1px solid #C9D2DC; border-radius: 8px; background: #FFFFFF; padding: 6px 10px; color: #111827; }}
QComboBox:focus {{ border-color: #1E293B; }}
QComboBox QAbstractItemView {{ background: #FFFFFF; border: 1px solid #C9D2DC; color: #111827; selection-background-color: #1E293B; selection-color: #FFFFFF; }}
QTableWidget {{ border: 1px solid #C9D2DC; gridline-color: #E2E8F0; background: #FFFFFF; alternate-background-color: #F8FAFC; color: #111827; }}
QTableWidget::item {{ background-color: #FFFFFF; color: #111827; }}
QTableWidget::item:alternate {{ background-color: #F8FAFC; }}
QTableWidget::item:selected {{ background: #1E293B; color: #FFFFFF; }}
QHeaderView::section {{ background: #E9EEF3; color: #475569; border: none; border-right: 1px solid #C9D2DC; border-bottom: 1px solid #C9D2DC; padding: 7px 10px; font-weight: 700; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #B8C2CE; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #B8C2CE; border-radius: 4px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit {{ border: 1px solid #C9D2DC; border-radius: 8px; background: #FFFFFF; padding: 7px 10px; color: #111827; selection-background-color: #1E293B; }}
QLineEdit:focus {{ border-color: #1E293B; }}
QDoubleSpinBox, QSpinBox {{ border: 1px solid #C9D2DC; border-radius: 8px; background: #FFFFFF; padding: 7px 10px; color: #111827; }}
QSplitter::handle {{ background: #C9D2DC; }}
QDialog {{ background: #FFFFFF; }}
QMessageBox {{ background: #FFFFFF; }}
QToolTip {{ background: #FFFFE1; color: #111827; border: 1px solid #767676; border-radius: 0px; padding: 5px 10px; font-size: 11px; }}
"""

DARK_QSS = f"""
QMainWindow, QWidget {{ background-color: #1E1E1E; color: #D4D4D4; font-family: {APP_FONT_FAMILY}; font-size: {APP_FONT_SIZE}px; }}
QTabWidget {{ background: #1E1E1E; }}
QTabWidget::pane {{ border: 1px solid #3E3E42; background: #252526; }}
QTabBar {{ background: #1E1E1E; }}
QTabBar::scroller {{ background: #1E1E1E; }}
QTabBar QToolButton {{ background: #1E1E1E; border: none; }}
QTabBar::tab {{ background: #1E1E1E; color: #9D9D9D; padding: 8px 16px; border: 1px solid #3E3E42; border-bottom: none; border-top-left-radius: 3px; border-top-right-radius: 3px; }}
QTabBar::tab:selected {{ background: #252526; color: #FFFFFF; font-weight: 700; border-bottom: 2px solid #5B8DEF; }}
QTabBar::tab:hover {{ background: #2D2D2D; color: #D4D4D4; }}
QGroupBox {{ border: 1px solid #3E3E42; border-radius: 3px; margin-top: 16px; padding-top: 14px; font-weight: 700; color: #D4D4D4; background: #252526; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #9D9D9D; font-size: 11px; letter-spacing: 0.2px; }}
QPushButton {{ background-color: #2D2D2D; color: #D4D4D4; border: 1px solid #3E3E42; border-radius: 3px; padding: 5px 12px; }}
QPushButton:hover {{ background-color: #3A3A3A; color: #FFFFFF; border-color: #5A5A5A; }}
QPushButton:disabled {{ color: #5A5A5A; background: #1E1E1E; border-color: #3E3E42; }}
QComboBox {{ border: 1px solid #3E3E42; border-radius: 3px; background: #252526; padding: 5px 10px; color: #D4D4D4; }}
QComboBox:focus {{ border-color: #5B8DEF; }}
QComboBox QAbstractItemView {{ background: #252526; border: 1px solid #3E3E42; color: #D4D4D4; selection-background-color: #2D2D2D; selection-color: #FFFFFF; }}
QTableWidget {{ border: 1px solid #3E3E42; gridline-color: #2D2D2D; background: #252526; alternate-background-color: #1E1E1E; color: #D4D4D4; }}
QTableWidget::item {{ background-color: #252526; color: #D4D4D4; }}
QTableWidget::item:alternate {{ background-color: #1E1E1E; }}
QTableWidget::item:selected {{ background: #3A4A6B; color: #FFFFFF; }}
QHeaderView::section {{ background: #1E1E1E; color: #9D9D9D; border: none; border-right: 1px solid #3E3E42; border-bottom: 1px solid #3E3E42; padding: 6px 10px; font-weight: 700; }}
QScrollBar:vertical {{ width: 7px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #5A5A5A; border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 7px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #5A5A5A; border-radius: 3px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit {{ border: 1px solid #3E3E42; border-radius: 3px; background: #3C3C3C; padding: 5px 10px; color: #D4D4D4; selection-background-color: #3A4A6B; }}
QLineEdit:focus {{ border-color: #5B8DEF; }}
QDoubleSpinBox, QSpinBox {{ border: 1px solid #3E3E42; border-radius: 3px; background: #3C3C3C; padding: 5px 10px; color: #D4D4D4; }}
QSplitter::handle {{ background: #3E3E42; }}
QDialog {{ background: #252526; color: #D4D4D4; }}
QMessageBox {{ background: #252526; color: #D4D4D4; }}
QScrollArea {{ background: transparent; border: none; }}
QToolTip {{ background: #252526; color: #D4D4D4; border: 1px solid #3E3E42; border-radius: 3px; padding: 5px 10px; font-size: 11px; }}
"""

GLOBAL_QSS = LIGHT_QSS

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
