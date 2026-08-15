import sys
import os
import logging
import threading
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log")
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True
)
logging.info("Starting Antigravity Limits Monitor...")

from core.models import AccountStatus
from core.config import ConfigManager, AppConfig
from core.collector import QuotaCollector
from ui.overlay import FloatingOverlay
from ui.tray import SystemTrayManager
from ui.settings_dialog import SettingsDialog



class LimitsAppController(QObject):
    """Main Application Controller."""

    status_ready = Signal(AccountStatus)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        logging.info("Initializing ConfigManager...")
        self.config_mgr = ConfigManager()
        self.config = self.config_mgr.config
        self.collector = QuotaCollector(self.config)
        self._is_fetching = False

        # Connect status signal
        self.status_ready.connect(self.on_status_received)

        logging.info("Initializing FloatingOverlay...")
        self.overlay = FloatingOverlay(self.config)
        logging.info("Initializing SystemTrayManager...")
        self.tray = SystemTrayManager(self.config)
        self.settings_dialog = None

        # Auto-refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.trigger_refresh)
        self.update_timer_interval()

        # Connect signals
        self.overlay.refresh_requested.connect(self.trigger_refresh)
        self.overlay.settings_requested.connect(self.open_settings)
        self.overlay.exit_requested.connect(self.quit_app)

        self.tray.refresh_requested.connect(self.trigger_refresh)
        self.tray.toggle_overlay_requested.connect(self.toggle_overlay)
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.exit_requested.connect(self.quit_app)

        # Show overlay
        logging.info("Showing overlay...")
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

        # Startup notification
        self.tray.show_notification(
            "Antigravity Limits Monitor",
            "Панель лимитов запущена и активна поверх всех окон."
        )

        # If --settings passed in CLI, open settings dialog on launch
        if "--settings" in sys.argv or "-s" in sys.argv:
            logging.info("Opening settings dialog on launch...")
            QTimer.singleShot(150, self.open_settings)

        # Initial fetch
        QTimer.singleShot(50, self.trigger_refresh)
        logging.info("LimitsAppController initialization finished.")

    def update_timer_interval(self):
        interval_ms = max(1, self.config.update_interval_min) * 60 * 1000
        self.timer.stop()
        self.timer.start(interval_ms)

    def trigger_refresh(self):
        if self._is_fetching:
            return
        self._is_fetching = True
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
            status = self.collector.fetch_status()
            self.status_ready.emit(status)
        except Exception as e:
            err_status = AccountStatus(
                is_connected=False,
                error_message=f"Ошибка: {str(e)[:40]}"
            )
            self.status_ready.emit(err_status)
        finally:
            self._is_fetching = False

    def on_status_received(self, status: AccountStatus):
        logging.info(f"Received status update: connected={status.is_connected}, models={len(status.models)}, email={status.email}")
        self.overlay.update_data(status)
        self.tray.update_status(status)

    def toggle_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()

    def open_settings(self):
        logging.info("open_settings called")
        if self.settings_dialog is None or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(self.config, self.collector)
            self.settings_dialog.settings_saved.connect(self.on_settings_saved)
            self.settings_dialog.refresh_requested.connect(self.trigger_refresh)
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            logging.info(f"Settings dialog shown! isVisible={self.settings_dialog.isVisible()}")
        else:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()

    def on_settings_saved(self, new_config: AppConfig):
        self.config = new_config
        self.collector.config = new_config
        self.overlay.config = new_config
        self.overlay.init_window_properties()
        self.overlay.apply_config_styles()
        self.overlay.show()
        self.update_timer_interval()
        self.trigger_refresh()

    def quit_app(self):
        # Save position before closing
        pos = self.overlay.pos()
        self.config.window_x = pos.x()
        self.config.window_y = pos.y()
        self.config_mgr.save(self.config)
        self.app.quit()


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Antigravity Limits Monitor")
    app.setOrganizationName("Antigravity")

    controller = LimitsAppController(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
