import os
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QFont, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from core.models import AccountStatus
from core.config import AppConfig


class SystemTrayManager(QObject):
    """Manages the Windows System Tray Icon, notifications, and context menu."""

    refresh_requested = Signal()
    toggle_overlay_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.tray_icon = QSystemTrayIcon(self)
        self.account_status = AccountStatus(is_connected=False)

        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._ico_green = os.path.join(self._base_dir, "assets", "icon.ico")
        self._ico_red = os.path.join(self._base_dir, "assets", "icon_red.ico")
        self._ico_amber = os.path.join(self._base_dir, "assets", "icon_amber.ico")

        self.init_icon()
        self.init_menu()
        self.tray_icon.activated.connect(self.on_tray_activated)

    def init_icon(self):
        if os.path.exists(self._ico_green):
            self.tray_icon.setIcon(QIcon(self._ico_green))
        else:
            pixmap = self.generate_icon_pixmap(color="#10b981")
            self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Antigravity Limits Monitor")
        self.tray_icon.setVisible(True)
        self.tray_icon.show()

    def generate_icon_pixmap(self, color: str = "#10b981") -> QPixmap:
        """Generates a high-contrast 64x64 tray icon."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background rounded badge with solid fill
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)

        # Text "AG"
        painter.setPen(QColor("#000000" if color != "#ef4444" else "#ffffff"))
        font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AG")

        painter.end()
        return pixmap

    def show_notification(self, title: str, message: str):
        """Shows Windows toast / balloon notification."""
        if self.tray_icon.isSystemTrayAvailable():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                3500
            )

    def init_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #18181c;
                color: #f4f4f5;
                border: 1px solid #27272a;
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
                background-color: #3f3f46;
            }
            QMenu::separator {
                height: 1px;
                background: #27272a;
                margin: 4px 6px;
            }
        """)

        # Account info header item
        self.header_action = QAction("Antigravity: Отключен", self.menu)
        self.header_action.setEnabled(False)
        self.menu.addAction(self.header_action)

        self.menu.addSeparator()

        # Dynamic Quota Summary submenu or items
        self.summary_menu = self.menu.addMenu("📊  Лимиты моделей")
        self.summary_menu.setEnabled(False)

        self.menu.addSeparator()

        # Action: Refresh
        self.act_refresh = QAction("🔄  Обновить сейчас", self.menu)
        self.act_refresh.triggered.connect(self.refresh_requested.emit)
        self.menu.addAction(self.act_refresh)

        # Action: Toggle HUD Overlay
        self.act_toggle = QAction("👁️  Показать / Скрыть панель", self.menu)
        self.act_toggle.triggered.connect(self.toggle_overlay_requested.emit)
        self.menu.addAction(self.act_toggle)

        # Action: Settings
        self.act_settings = QAction("⚙️  Настройки...", self.menu)
        self.act_settings.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(self.act_settings)

        self.menu.addSeparator()

        # Action: Exit
        self.act_exit = QAction("❌  Выход", self.menu)
        self.act_exit.triggered.connect(self.exit_requested.emit)
        self.menu.addAction(self.act_exit)

        self.tray_icon.setContextMenu(self.menu)

    def update_status(self, status: AccountStatus):
        self.account_status = status

        if status.is_connected:
            if os.path.exists(self._ico_green):
                self.tray_icon.setIcon(QIcon(self._ico_green))
            else:
                self.tray_icon.setIcon(QIcon(self.generate_icon_pixmap(color="#10b981")))
            plan_str = f" ({status.plan.plan_name})" if status.plan.plan_name else ""
            self.header_action.setText(f"👤 {status.email or 'Подключено'}{plan_str}")
            
            # Update summary submenu
            self.summary_menu.clear()
            self.summary_menu.setEnabled(True)

            tip_lines = [f"Antigravity: {status.email}"]

            for m in status.models:
                cd_str = f" [{m.reset_countdown}]" if m.reset_countdown else ""
                item_text = f"{m.label}: {m.percentage}%{cd_str}"
                act = self.summary_menu.addAction(item_text)
                act.setEnabled(False)
                tip_lines.append(f"• {m.label}: {m.percentage}%")

            self.tray_icon.setToolTip("\n".join(tip_lines[:8]))
        else:
            if os.path.exists(self._ico_red):
                self.tray_icon.setIcon(QIcon(self._ico_red))
            else:
                self.tray_icon.setIcon(QIcon(self.generate_icon_pixmap(color="#ef4444")))
            self.header_action.setText("⚠️ Antigravity не запущен")
            self.summary_menu.clear()
            self.summary_menu.setEnabled(False)
            self.tray_icon.setToolTip("Antigravity: Отключен\n(Запустите Antigravity или откройте настройки)")

    def on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_overlay_requested.emit()
