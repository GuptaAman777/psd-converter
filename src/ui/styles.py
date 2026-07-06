from src.constants import COLORS

STYLES = {
    'scroll_area': f"""
        QScrollArea {{ border: none; background-color: transparent; }}
        QScrollBar:vertical {{ background-color: #252535; width: 10px; border-radius: 5px; }}
        QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    """,
    'scroll_area_hv': f"""
        QScrollArea {{ border: none; background-color: transparent; }}
        QScrollBar:vertical {{ background-color: #252535; width: 10px; border-radius: 5px; }}
        QScrollBar::handle:vertical {{ background-color: #4d4d5f; border-radius: 5px; min-height: 20px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{ background-color: #252535; height: 10px; border-radius: 5px; }}
        QScrollBar::handle:horizontal {{ background-color: #4d4d5f; border-radius: 5px; min-width: 20px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background-color: transparent; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    """,
    'action_button': f"""
        QPushButton {{ background-color: {COLORS['secondary']}; color: {COLORS['text']}; border: none; border-radius: 8px; padding: 8px; font-weight: 600; }}
        QPushButton:hover {{ background-color: {COLORS['hover']}; }}
    """,
    'action_button_red': f"""
        QPushButton {{ background-color: {COLORS['error']}; color: white; border: none; border-radius: 8px; padding: 8px; font-weight: 600; }}
        QPushButton:hover {{ background-color: {COLORS['error_hover']}; }}
    """,
    'action_button_yellow': f"""
        QPushButton {{ background-color: #FFB940; color: {COLORS['text']}; border: none; border-radius: 8px; padding: 10px; font-weight: 600; }}
        QPushButton:hover {{ background-color: #C4821A; }}
    """,
    'primary_button': f"""
        QPushButton {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: 600; }}
        QPushButton:hover {{ background-color: {COLORS['hover']}; }}
    """,
    'primary_button_large': f"""
        QPushButton {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: 600; margin-top: 10px; }}
        QPushButton:hover {{ background-color: {COLORS['hover']}; }}
        QPushButton:disabled {{ background-color: {COLORS['disabled']}; color: {COLORS['text_secondary']}; }}
    """,
    'message_box': f"""
        QMessageBox {{ background-color: {COLORS['background']}; color: {COLORS['text']}; }}
        QLabel {{ color: {COLORS['text']}; font-size: 12px; }}
        QPushButton {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; min-width: 80px; }}
        QPushButton:hover {{ background-color: {COLORS['hover']}; }}
    """,
    'message_box_wide': f"""
        QMessageBox {{ background-color: {COLORS['background']}; color: {COLORS['text']}; }}
        QLabel {{ color: {COLORS['text']}; font-size: 12px; }}
        QPushButton {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; min-width: 150px; }}
        QPushButton:hover {{ background-color: {COLORS['hover']}; }}
    """,
    'progress_bar': f"""
        QProgressBar {{ border: 1px solid {COLORS['border']}; border-radius: 5px; background-color: {COLORS['panel']}; height: 20px; text-align: center; padding: 0px; }}
        QProgressBar::chunk {{ background-color: {COLORS['primary']}; border-radius: 4px; margin: 1px; border: 1px solid {COLORS['primary']}; min-width: 10px; }}
    """,
}

def button_style(bg_color=COLORS['primary'], text_color=COLORS['text'], hover_color=COLORS['hover'], padding="8px", radius="8px", font_weight="600"):
    return f"""
        QPushButton {{ background-color: {bg_color}; color: {text_color}; border: none; border-radius: {radius}; padding: {padding}; font-weight: {font_weight}; }}
        QPushButton:hover {{ background-color: {hover_color}; }}
        QPushButton:disabled {{ background-color: {COLORS['disabled']}; color: {COLORS['text_secondary']}; }}
    """

def scrollbar_style():
    return STYLES['scroll_area']

def scrollbar_hv_style():
    return STYLES['scroll_area_hv']

def message_box_style():
    return STYLES['message_box']

def message_box_wide_style():
    return STYLES['message_box_wide']

def group_box_style():
    return f"""
        QGroupBox {{ background-color: {COLORS['panel']}; border-radius: 8px; margin-top: 20px; border: 1px solid {COLORS['border']}; font-weight: bold; padding-top: 15px; }}
        QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: {COLORS['primary']}; }}
    """

def input_style():
    return f"""
        QLineEdit, QTextEdit, QComboBox {{ background-color: {COLORS['background']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 5px; }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 1px solid {COLORS['primary']}; }}
    """
