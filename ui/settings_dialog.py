from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QSlider,
    QLineEdit,
    QGroupBox,
    QColorDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QFormLayout,
)

from core.models import AccountStatus
from core.config import AppConfig, ConfigManager
from core.collector import QuotaCollector
from .styles import build_settings_stylesheet


class ColorButton(QPushButton):
    """Button that displays a color preview and opens a QColorDialog when clicked."""

    color_changed = Signal(str)

    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(56, 26)
        self.update_style()
        self.clicked.connect(self.choose_color)

    def set_color(self, color_hex: str):
        self.color_hex = color_hex
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                border: 2px solid #52525b;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.color_hex), self, "Выберите цвет")
        if color.isValid():
            self.color_hex = color.name()
            self.update_style()
            self.color_changed.emit(self.color_hex)


class SettingsDialog(QDialog):
    """Complete Settings and Authorization window for Antigravity Limits Monitor."""

    settings_saved = Signal(AppConfig)
    refresh_requested = Signal()

    def __init__(self, config: AppConfig, collector: QuotaCollector, parent=None):
        super().__init__(parent)
        self.config = config
        self.collector = collector
        self.latest_status = AccountStatus(is_connected=False)

        self.setWindowTitle("Настройки Antigravity Limits Monitor")
        self.setMinimumSize(480, 520)
        self.resize(520, 560)
        self.setStyleSheet(build_settings_stylesheet(self.config))

        self.init_ui()
        self.load_values()
        self.test_connection()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Tab Widget
        self.tabs = QTabWidget(self)
        self.tab_appearance = QWidget()
        self.tab_models = QWidget()
        self.tab_sync = QWidget()
        self.tab_auth = QWidget()

        self.tabs.addTab(self.tab_appearance, "🎨 Внешний вид")
        self.tabs.addTab(self.tab_models, "🤖 Модели")
        self.tabs.addTab(self.tab_sync, "⏱️ Обновление")
        self.tabs.addTab(self.tab_auth, "🔐 Авторизация и Связь")

        self.init_appearance_tab()
        self.init_models_tab()
        self.init_sync_tab()
        self.init_auth_tab()

        main_layout.addWidget(self.tabs)

        # Bottom Buttons (Save / Cancel / Apply)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Сохранить и Применить")
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.clicked.connect(self.save_and_apply)
        bottom_layout.addWidget(self.btn_save)

        main_layout.addLayout(bottom_layout)

    # --- Tab 1: Appearance ---
    def init_appearance_tab(self):
        layout = QVBoxLayout(self.tab_appearance)

        # Size & Layout Group
        grp_size = QGroupBox("Размер и параметры панели")
        form_size = QFormLayout(grp_size)
        form_size.setSpacing(8)

        # Font size
        self.spin_font = QSpinBox()
        self.spin_font.setRange(7, 14)
        form_size.addRow("Размер шрифта:", self.spin_font)

        # Opacity slider
        opacity_layout = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(40, 100)
        self.lbl_opacity = QLabel("92%")
        self.slider_opacity.valueChanged.connect(
            lambda v: self.lbl_opacity.setText(f"{v}%")
        )
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.lbl_opacity)
        form_size.addRow("Непрозрачность окна:", opacity_layout)

        # Toggles
        self.chk_ontop = QCheckBox("Поверх всех окон (Always on Top)")
        form_size.addRow(self.chk_ontop)

        self.chk_countdown = QCheckBox("Показывать таймер сброса квоты (↻ 45м)")
        form_size.addRow(self.chk_countdown)

        layout.addWidget(grp_size)

        # Colors Group
        grp_colors = QGroupBox("Цветовая палитра")
        form_colors = QFormLayout(grp_colors)
        form_colors.setSpacing(6)

        # Theme presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Пресеты:"))
        btn_dark = QPushButton("Dark Sleek")
        btn_dark.clicked.connect(lambda: self.apply_preset("#121216", "#f4f4f5", "#10b981"))
        preset_layout.addWidget(btn_dark)

        btn_black = QPushButton("OLED Black")
        btn_black.clicked.connect(lambda: self.apply_preset("#000000", "#ffffff", "#06b6d4"))
        preset_layout.addWidget(btn_black)

        btn_slate = QPushButton("Midnight Blue")
        btn_slate.clicked.connect(lambda: self.apply_preset("#0f172a", "#f8fafc", "#38bdf8"))
        preset_layout.addWidget(btn_slate)
        form_colors.addRow(preset_layout)

        # Individual color buttons
        self.btn_bg_color = ColorButton(self.config.bg_color)
        form_colors.addRow("Цвет фона:", self.btn_bg_color)

        self.btn_text_color = ColorButton(self.config.text_color)
        form_colors.addRow("Цвет текста:", self.btn_text_color)

        self.btn_high_color = ColorButton(self.config.bar_color_high)
        form_colors.addRow("Шкала > 50% (Высокая):", self.btn_high_color)

        self.btn_med_color = ColorButton(self.config.bar_color_med)
        form_colors.addRow("Шкала 20-50% (Средняя):", self.btn_med_color)

        self.btn_low_color = ColorButton(self.config.bar_color_low)
        form_colors.addRow("Шкала < 20% (Низкая):", self.btn_low_color)

        layout.addWidget(grp_colors)
        layout.addStretch()

    def apply_preset(self, bg: str, text: str, high: str):
        self.btn_bg_color.set_color(bg)
        self.btn_text_color.set_color(text)
        self.btn_high_color.set_color(high)

    # --- Tab 2: Models ---
    def init_models_tab(self):
        layout = QVBoxLayout(self.tab_models)

        grp_grouping = QGroupBox("Отображение моделей")
        grp_layout = QVBoxLayout(grp_grouping)

        self.chk_group_models = QCheckBox("Группировать однотипные варианты (High/Med/Low)")
        self.chk_group_models.setToolTip(
            "Объединяет Gemini 3.7 (High/Medium/Low) в одну общую строку для компактности"
        )
        self.chk_group_models.toggled.connect(self.refresh_models_list)
        grp_layout.addWidget(self.chk_group_models)
        layout.addWidget(grp_grouping)

        grp_list = QGroupBox("Список отображаемых моделей")
        list_layout = QVBoxLayout(grp_list)

        self.list_models = QListWidget()
        list_layout.addWidget(self.list_models)

        lbl_hint = QLabel("Отметьте галочками модели, которые должны отображаться в оверлее.")
        lbl_hint.setStyleSheet("color: #71717a; font-size: 8pt;")
        list_layout.addWidget(lbl_hint)

        layout.addWidget(grp_list)

    def refresh_models_list(self):
        """Populates the models list based on latest discovered models."""
        self.list_models.clear()
        if not self.latest_status.is_connected or not self.latest_status.models:
            item = QListWidgetItem("Нет данных о моделях (нажмите Проверить связь)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_models.addItem(item)
            return

        for model in self.latest_status.models:
            item = QListWidgetItem(f"{model.label} ({model.percentage}%)")
            item.setData(Qt.ItemDataRole.UserRole, model.label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # Check state
            if model.label in self.config.hidden_models:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
            self.list_models.addItem(item)

    # --- Tab 3: Sync & Timers ---
    def init_sync_tab(self):
        layout = QVBoxLayout(self.tab_sync)

        grp_timing = QGroupBox("Тайминги и триггеры")
        form_timing = QFormLayout(grp_timing)
        form_timing.setSpacing(10)

        # Interval
        self.combo_interval = QComboBox()
        self.combo_interval.addItem("1 минута", 1)
        self.combo_interval.addItem("5 минут", 5)
        self.combo_interval.addItem("15 минут", 15)
        self.combo_interval.addItem("30 минут (По умолчанию)", 30)
        self.combo_interval.addItem("60 минут", 60)
        form_timing.addRow("Автообновление лимитов:", self.combo_interval)

        # Click to refresh
        self.chk_click_refresh = QCheckBox("Обновлять мгновенно при клике на панель")
        form_timing.addRow(self.chk_click_refresh)

        layout.addWidget(grp_timing)

        # Manual Action
        grp_manual = QGroupBox("Ручное действие")
        box_manual = QHBoxLayout(grp_manual)
        btn_refresh_now = QPushButton("🔄  Обновить лимиты прямо сейчас")
        btn_refresh_now.clicked.connect(self.manual_refresh_action)
        box_manual.addWidget(btn_refresh_now)
        layout.addWidget(grp_manual)

        layout.addStretch()

    def manual_refresh_action(self):
        self.refresh_requested.emit()
        self.test_connection()

    # --- Tab 4: Auth & Connection ---
    def init_auth_tab(self):
        layout = QVBoxLayout(self.tab_auth)

        # Status Banner
        self.grp_status = QGroupBox("Текущий статус подключения")
        form_status = QFormLayout(self.grp_status)

        self.lbl_conn_status = QLabel("Проверка...")
        form_status.addRow("Статус:", self.lbl_conn_status)

        self.lbl_email = QLabel("—")
        form_status.addRow("Аккаунт:", self.lbl_email)

        self.lbl_plan = QLabel("—")
        form_status.addRow("Тарифный план:", self.lbl_plan)

        self.lbl_credits = QLabel("—")
        form_status.addRow("Кредиты плана:", self.lbl_credits)

        layout.addWidget(self.grp_status)

        # Diagnostics & Overrides
        grp_diag = QGroupBox("Диагностика Language Server")
        form_diag = QFormLayout(grp_diag)

        self.lbl_pid = QLabel("—")
        form_diag.addRow("PID процесса:", self.lbl_pid)

        self.lbl_port = QLabel("—")
        form_diag.addRow("RPC Порт:", self.lbl_port)

        self.lbl_token = QLabel("—")
        form_diag.addRow("CSRF Токен:", self.lbl_token)

        self.btn_retest = QPushButton("🔍  Проверить подключение")
        self.btn_retest.clicked.connect(self.test_connection)
        form_diag.addRow(self.btn_retest)

        layout.addWidget(grp_diag)

        # Manual Mode Group
        grp_manual_mode = QGroupBox("Ручной ввод (для нестандартных установок)")
        form_man = QFormLayout(grp_manual_mode)

        self.chk_manual = QCheckBox("Использовать ручные настройки вместо автопоиска")
        form_man.addRow(self.chk_manual)

        self.edit_manual_port = QSpinBox()
        self.edit_manual_port.setRange(0, 65535)
        form_man.addRow("Порт RPC:", self.edit_manual_port)

        self.edit_manual_token = QLineEdit()
        self.edit_manual_token.setPlaceholderText("Вставьте CSRF Token...")
        form_man.addRow("CSRF Токен:", self.edit_manual_token)

        layout.addWidget(grp_manual_mode)
        layout.addStretch()

    def test_connection(self):
        self.lbl_conn_status.setText("⏳ Опрос локального сервера...")
        status = self.collector.fetch_status()
        self.latest_status = status

        if status.is_connected:
            self.lbl_conn_status.setText("🟢 Подключено (Активен)")
            self.lbl_conn_status.setStyleSheet("color: #10b981; font-weight: bold;")
            self.lbl_email.setText(status.email or "Авторизован")
            self.lbl_plan.setText(f"{status.plan.plan_name} ({status.plan.teams_tier})")
            self.lbl_credits.setText(
                f"Prompt: {status.plan.available_prompt_credits} | Flow: {status.plan.available_flow_credits}"
            )
            self.lbl_pid.setText(str(status.pid or "Auto"))
            self.lbl_port.setText(str(status.port or "Auto"))
            self.lbl_token.setText(
                f"{status.csrf_token[:8]}...{status.csrf_token[-8:]}"
                if status.csrf_token and len(status.csrf_token) > 16
                else (status.csrf_token or "—")
            )
        else:
            self.lbl_conn_status.setText("🔴 Отключено")
            self.lbl_conn_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.lbl_email.setText("—")
            self.lbl_plan.setText("—")
            self.lbl_credits.setText("—")
            self.lbl_pid.setText("Не найден")
            self.lbl_port.setText("—")
            self.lbl_token.setText("—")

        self.refresh_models_list()

    def load_values(self):
        """Loads values from AppConfig into widgets."""
        self.spin_font.setValue(self.config.font_size)
        self.slider_opacity.setValue(int(self.config.opacity * 100))
        self.lbl_opacity.setText(f"{int(self.config.opacity * 100)}%")
        self.chk_ontop.setChecked(self.config.always_on_top)
        self.chk_countdown.setChecked(self.config.show_reset_countdown)

        self.btn_bg_color.set_color(self.config.bg_color)
        self.btn_text_color.set_color(self.config.text_color)
        self.btn_high_color.set_color(self.config.bar_color_high)
        self.btn_med_color.set_color(self.config.bar_color_med)
        self.btn_low_color.set_color(self.config.bar_color_low)

        self.chk_group_models.setChecked(self.config.group_similar_models)
        self.chk_click_refresh.setChecked(self.config.refresh_on_click)

        # Interval combo
        idx = self.combo_interval.findData(self.config.update_interval_min)
        if idx >= 0:
            self.combo_interval.setCurrentIndex(idx)
        else:
            self.combo_interval.setCurrentIndex(3)  # default 30 min

        # Manual mode
        self.chk_manual.setChecked(self.config.manual_mode)
        self.edit_manual_port.setValue(self.config.manual_port)
        self.edit_manual_token.setText(self.config.manual_token)

    def save_and_apply(self):
        """Saves values into config and emits settings_saved."""
        self.config.font_size = self.spin_font.value()
        self.config.opacity = self.slider_opacity.value() / 100.0
        self.config.always_on_top = self.chk_ontop.isChecked()
        self.config.show_reset_countdown = self.chk_countdown.isChecked()

        self.config.bg_color = self.btn_bg_color.color_hex
        self.config.text_color = self.btn_text_color.color_hex
        self.config.bar_color_high = self.btn_high_color.color_hex
        self.config.bar_color_med = self.btn_med_color.color_hex
        self.config.bar_color_low = self.btn_low_color.color_hex

        self.config.group_similar_models = self.chk_group_models.isChecked()
        self.config.update_interval_min = self.combo_interval.currentData()
        self.config.refresh_on_click = self.chk_click_refresh.isChecked()

        # Hidden models from list
        hidden = []
        for i in range(self.list_models.count()):
            item = self.list_models.item(i)
            if item.checkState() == Qt.CheckState.Unchecked:
                label = item.data(Qt.ItemDataRole.UserRole)
                if label:
                    hidden.append(label)
        self.config.hidden_models = hidden

        # Manual connection
        self.config.manual_mode = self.chk_manual.isChecked()
        self.config.manual_port = self.edit_manual_port.value()
        self.config.manual_token = self.edit_manual_token.text().strip()

        ConfigManager().save(self.config)
        self.settings_saved.emit(self.config)
        self.accept()
