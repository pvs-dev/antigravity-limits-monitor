from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QMouseEvent, QContextMenuEvent, QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QMenu,
    QGraphicsOpacityEffect,
    QApplication,
)

from core.models import AccountStatus, ModelQuota
from core.config import AppConfig
from .styles import build_overlay_stylesheet, get_quota_color


class QuotaRowWidget(QWidget):
    """A compact single row displaying Model Name, Percentage, Reset Time and Progress Bar."""

    def __init__(self, quota: ModelQuota, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.quota = quota
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 1)
        layout.setSpacing(1)

        # Top line: Model Name (Left) + Countdown (Center) + Percentage (Right)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(3)

        # Model label (compact)
        self.name_label = QLabel(self.quota.label)
        self.name_label.setObjectName("ModelLabel")
        top_layout.addWidget(self.name_label)

        top_layout.addStretch()

        # Reset countdown
        if self.config.show_reset_countdown and self.quota.reset_countdown:
            self.cd_label = QLabel(f"↻ {self.quota.reset_countdown}")
            self.cd_label.setObjectName("CountdownLabel")
            top_layout.addWidget(self.cd_label)

        # Percentage label
        pct = self.quota.percentage
        self.pct_label = QLabel(f"{pct}%")
        self.pct_label.setObjectName("PercentLabel")
        color = get_quota_color(pct, self.config)
        self.pct_label.setStyleSheet(f"color: {color};")
        top_layout.addWidget(self.pct_label)

        layout.addLayout(top_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(pct)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 1px;
            }}
        """)
        layout.addWidget(self.progress)

        # Tooltip for details
        tip_text = (
            f"<b>{self.quota.label}</b><br/>"
            f"Остаток: <b>{pct}%</b><br/>"
            f"Сброс квоты: {self.quota.reset_countdown or '—'}<br/>"
            f"UTC время: {self.quota.reset_time or '—'}"
        )
        self.setToolTip(tip_text)


class FloatingOverlay(QWidget):
    """Ultra-compact, frameless, draggable, always-on-top floating HUD overlay."""

    refresh_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.account_status: AccountStatus = AccountStatus(is_connected=False)
        self.drag_position = QPoint()
        self._is_dragging = False

        self.init_window_properties()
        self.init_ui()
        self.apply_config_styles()

    def init_window_properties(self):
        # Frameless, Always on Top, Top-level window
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self.config.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("Antigravity Limits HUD")

        # Set initial geometry constraints
        self.setMinimumWidth(150)
        self.setMaximumWidth(220)

        # Validate saved coordinates across all connected screens
        target_x = self.config.window_x
        target_y = self.config.window_y
        pos_valid = False

        if target_x >= 0 and target_y >= 0:
            for s in QApplication.screens():
                if s.geometry().contains(target_x, target_y):
                    pos_valid = True
                    break

        if pos_valid:
            self.move(target_x, target_y)
        else:
            # Default to top-left of primary screen with offset
            primary = QApplication.primaryScreen()
            if primary:
                avail = primary.availableGeometry()
                self.move(avail.x() + 80, avail.y() + 80)
            else:
                self.move(80, 80)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Background Frame container
        self.frame = QFrame(self)
        self.frame.setObjectName("MainFrame")
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(6, 3, 6, 4)
        self.frame_layout.setSpacing(2)

        # Header bar
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 1)
        self.header_layout.setSpacing(3)

        # Connection status dot
        self.status_dot = QLabel()
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedSize(5, 5)
        self.status_dot.setStyleSheet("background-color: #71717a; border-radius: 2.5px;")
        self.header_layout.addWidget(self.status_dot)

        # Header Title
        self.header_title = QLabel("ANTIGRAVITY")
        self.header_title.setObjectName("HeaderTitle")
        self.header_layout.addWidget(self.header_title)

        self.header_layout.addStretch()

        # Last updated / click hint
        self.header_sub = QLabel("клик: обновить")
        self.header_sub.setObjectName("HeaderTitle")
        self.header_sub.setStyleSheet("font-size: 6.5pt; color: #71717a;")
        self.header_layout.addWidget(self.header_sub)

        self.frame_layout.addLayout(self.header_layout)

        # Content container for model rows
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(2)
        self.frame_layout.addWidget(self.content_widget)

        self.main_layout.addWidget(self.frame)

        # Set initial status message
        self.set_disconnected_state("Поиск Antigravity...")

    def apply_config_styles(self):
        self.setStyleSheet(build_overlay_stylesheet(self.config))
        self.setWindowOpacity(self.config.opacity)

    def set_disconnected_state(self, message: str):
        self.status_dot.setStyleSheet("background-color: #ef4444; border-radius: 3px;")
        self.clear_content_layout()

        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #a1a1aa; font-size: 8pt; padding: 4px 0;")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(msg_label)
        self.adjustSize()

    def update_data(self, status: AccountStatus):
        self.account_status = status
        self.clear_content_layout()

        if not status.is_connected:
            self.set_disconnected_state(status.error_message or "Antigravity отключен")
            return

        # Connected state
        self.status_dot.setStyleSheet("background-color: #10b981; border-radius: 3px;")
        
        if status.last_updated:
            time_str = status.last_updated.strftime("%H:%M")
            self.header_sub.setText(f"обн. {time_str}")

        if not status.models:
            empty_lbl = QLabel("Нет активных моделей")
            empty_lbl.setStyleSheet("color: #71717a; font-size: 8pt;")
            self.content_layout.addWidget(empty_lbl)
        else:
            for model in status.models:
                row = QuotaRowWidget(model, self.config, self)
                self.content_layout.addWidget(row)

        self.adjustSize()

    def clear_content_layout(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # --- Mouse interaction: Click to refresh & Drag-and-drop ---

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.config.window_x = new_pos.x()
            self.config.window_y = new_pos.y()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_dragging:
                # Single click without movement triggers manual refresh
                if self.config.refresh_on_click:
                    self.flash_refresh_indicator()
                    self.refresh_requested.emit()
            self._is_dragging = False
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.settings_requested.emit()
            event.accept()

    def flash_refresh_indicator(self):
        """Briefly changes the status dot color to indicate refresh."""
        self.status_dot.setStyleSheet("background-color: #6366f1; border-radius: 3px;")
        self.header_sub.setText("обновление...")
        QTimer.singleShot(600, self._restore_status_dot)

    def _restore_status_dot(self):
        if self.account_status.is_connected:
            self.status_dot.setStyleSheet("background-color: #10b981; border-radius: 3px;")
            if self.account_status.last_updated:
                self.header_sub.setText(f"обн. {self.account_status.last_updated.strftime('%H:%M')}")
        else:
            self.status_dot.setStyleSheet("background-color: #ef4444; border-radius: 3px;")
            self.header_sub.setText("клик: обновить")

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1c1c24;
                color: #f4f4f5;
                border: 1px solid #2e2e38;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 9pt;
            }
            QMenu::item {
                padding: 5px 20px 5px 10px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b3b47;
            }
            QMenu::separator {
                height: 1px;
                background: #2e2e38;
                margin: 4px 6px;
            }
        """)

        act_refresh = menu.addAction("🔄  Обновить сейчас")
        act_settings = menu.addAction("⚙️  Настройки")
        menu.addSeparator()

        act_ontop = menu.addAction("📌  Поверх всех окон")
        act_ontop.setCheckable(True)
        act_ontop.setChecked(self.config.always_on_top)

        menu.addSeparator()
        act_hide = menu.addAction("👁️  Скрыть в трей")
        act_exit = menu.addAction("❌  Выход")

        action = menu.exec(event.globalPos())
        if action == act_refresh:
            self.flash_refresh_indicator()
            self.refresh_requested.emit()
        elif action == act_settings:
            self.settings_requested.emit()
        elif action == act_ontop:
            self.config.always_on_top = act_ontop.isChecked()
            self.init_window_properties()
            self.show()
        elif action == act_hide:
            self.hide()
        elif action == act_exit:
            self.exit_requested.emit()
