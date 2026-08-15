from core.config import AppConfig


def get_quota_color(percentage: int, config: AppConfig) -> str:
    """Returns color hex string depending on quota percentage."""
    if percentage >= 50:
        return config.bar_color_high
    elif percentage >= 20:
        return config.bar_color_med
    else:
        return config.bar_color_low


def build_overlay_stylesheet(config: AppConfig) -> str:
    """Builds CSS/QSS for the compact floating HUD overlay."""
    fs = config.font_size
    return f"""
        #MainFrame {{
            background-color: {config.bg_color};
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 6px;
        }}
        QLabel {{
            color: {config.text_color};
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: {fs}pt;
            padding: 0px;
            margin: 0px;
        }}
        #HeaderTitle {{
            color: {config.text_secondary_color};
            font-size: {max(6, fs - 1)}pt;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        #StatusDot {{
            border-radius: 3px;
        }}
        #ModelLabel {{
            color: {config.text_color};
            font-size: {fs}pt;
            font-weight: 500;
        }}
        #PercentLabel {{
            font-size: {fs}pt;
            font-weight: 700;
            font-family: 'Consolas', 'Cascadia Code', monospace;
        }}
        #CountdownLabel {{
            color: {config.text_secondary_color};
            font-size: {max(6, fs - 2)}pt;
            font-family: 'Consolas', 'Cascadia Code', monospace;
        }}
        QProgressBar {{
            background-color: {config.bar_bg_color};
            border: none;
            border-radius: 1px;
            text-align: right;
            max-height: 3px;
            min-height: 3px;
        }}
        QProgressBar::chunk {{
            border-radius: 1px;
        }}
        QToolTip {{
            background-color: #1f242d;
            color: #ffffff;
            border: 1px solid #3b4252;
            border-radius: 4px;
            padding: 3px 6px;
            font-size: {fs}pt;
        }}
    """


def build_settings_stylesheet(config: AppConfig) -> str:
    """Builds modern stylesheet for Settings Dialog."""
    return f"""
        QDialog {{
            background-color: #18181c;
            color: #f4f4f5;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }}
        QTabWidget::pane {{
            border: 1px solid #27272a;
            background-color: #18181c;
            border-radius: 6px;
            padding: 12px;
        }}
        QTabBar::tab {{
            background-color: #27272a;
            color: #a1a1aa;
            padding: 8px 16px;
            margin-right: 4px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            background-color: #3f3f46;
            color: #ffffff;
        }}
        QTabBar::tab:hover {{
            background-color: #323238;
            color: #ffffff;
        }}
        QGroupBox {{
            font-weight: 600;
            border: 1px solid #2e2e36;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 14px;
            color: #e4e4e7;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #a1a1aa;
        }}
        QLabel {{
            color: #e4e4e7;
            font-size: 10pt;
        }}
        QLineEdit, QSpinBox, QComboBox {{
            background-color: #27272a;
            color: #ffffff;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 5px 8px;
            font-size: 10pt;
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid #6366f1;
        }}
        QCheckBox {{
            color: #e4e4e7;
            spacing: 8px;
            font-size: 10pt;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #52525b;
            background-color: #27272a;
        }}
        QCheckBox::indicator:checked {{
            background-color: #6366f1;
            border-color: #6366f1;
        }}
        QPushButton {{
            background-color: #3f3f46;
            color: #ffffff;
            border: 1px solid #52525b;
            border-radius: 5px;
            padding: 6px 14px;
            font-size: 10pt;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: #52525b;
        }}
        QPushButton:pressed {{
            background-color: #27272a;
        }}
        QPushButton#PrimaryBtn {{
            background-color: #4f46e5;
            border: 1px solid #6366f1;
        }}
        QPushButton#PrimaryBtn:hover {{
            background-color: #4338ca;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: #27272a;
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: #6366f1;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: #ffffff;
            width: 14px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 7px;
        }}
        QListWidget {{
            background-color: #202025;
            border: 1px solid #2e2e36;
            border-radius: 6px;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 6px;
            border-radius: 4px;
            color: #e4e4e7;
        }}
        QListWidget::item:hover {{
            background-color: #2b2b33;
        }}
        QListWidget::item:selected {{
            background-color: #3b3b47;
        }}
    """
