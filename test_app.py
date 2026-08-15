import unittest
import os
import sys
import json
from datetime import datetime, timezone, timedelta

from core.models import ModelQuota, PlanStatus, AccountStatus
from core.config import AppConfig, ConfigManager
from core.collector import QuotaCollector
from ui.styles import get_quota_color, build_overlay_stylesheet, build_settings_stylesheet


class TestCoreModels(unittest.TestCase):
    def test_model_quota_percentage(self):
        m = ModelQuota(label="Test Model", remaining_fraction=0.854)
        self.assertEqual(m.percentage, 85)

        m0 = ModelQuota(label="Test 0", remaining_fraction=0.0)
        self.assertEqual(m0.percentage, 0)

        m1 = ModelQuota(label="Test 1", remaining_fraction=1.0)
        self.assertEqual(m1.percentage, 100)

    def test_countdown_formatting(self):
        # 30 mins in future
        future_time = (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat()
        m = ModelQuota(label="Test", remaining_fraction=0.5, reset_time=future_time)
        self.assertIn("м", m.reset_countdown)

        # 2 hours in future
        future_2h = (datetime.now(timezone.utc) + timedelta(hours=2, minutes=10)).isoformat()
        m2 = ModelQuota(label="Test", remaining_fraction=0.5, reset_time=future_2h)
        self.assertIn("2ч", m2.reset_countdown)


class TestConfig(unittest.TestCase):
    def test_config_save_load(self):
        tmp_path = os.path.join(os.path.dirname(__file__), "test_config.json")
        try:
            mgr = ConfigManager(tmp_path)
            cfg = mgr.config
            cfg.font_size = 11
            cfg.bg_color = "#112233"
            mgr.save(cfg)

            mgr2 = ConfigManager(tmp_path)
            self.assertEqual(mgr2.config.font_size, 11)
            self.assertEqual(mgr2.config.bg_color, "#112233")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestCollector(unittest.TestCase):
    def test_live_or_mock_collector(self):
        cfg = AppConfig()
        collector = QuotaCollector(cfg)
        status = collector.fetch_status()
        # Should return an AccountStatus instance
        self.assertIsInstance(status, AccountStatus)
        if status.is_connected:
            self.assertTrue(len(status.models) > 0)
            self.assertIsNotNone(status.email)
            print(f"Live Test Succeeded: {status.email}, {len(status.models)} models found.")
        else:
            print(f"Collector returned disconnected state: {status.error_message}")


class TestQtComponents(unittest.TestCase):
    def test_ui_components(self):
        from PySide6.QtWidgets import QApplication
        from ui.overlay import FloatingOverlay
        from ui.tray import SystemTrayManager
        from ui.settings_dialog import SettingsDialog

        app = QApplication.instance() or QApplication(sys.argv)
        cfg = AppConfig()
        collector = QuotaCollector(cfg)

        overlay = FloatingOverlay(cfg)
        self.assertIsNotNone(overlay)

        # Test updating with status
        dummy_status = AccountStatus(
            is_connected=True,
            email="test@example.com",
            plan=PlanStatus(plan_name="Pro"),
            models=[
                ModelQuota(label="Gemini 3.7 Flash", remaining_fraction=0.75),
                ModelQuota(label="Claude Sonnet 4.6", remaining_fraction=0.15),
            ],
            last_updated=datetime.now()
        )
        overlay.update_data(dummy_status)

        tray = SystemTrayManager(cfg)
        tray.update_status(dummy_status)

        dialog = SettingsDialog(cfg, collector)
        self.assertIsNotNone(dialog)


if __name__ == "__main__":
    unittest.main()
