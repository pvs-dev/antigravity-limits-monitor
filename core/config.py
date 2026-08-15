import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class AppConfig:
    # General / Update settings
    update_interval_min: int = 30
    refresh_on_click: bool = True
    always_on_top: bool = True
    
    # Appearance
    opacity: float = 0.92
    font_size: int = 8
    compact_mode: bool = True
    show_reset_countdown: bool = True
    show_header: bool = True
    
    # Colors
    bg_color: str = "#121216"
    card_bg_color: str = "#1c1c24"
    text_color: str = "#f4f4f5"
    text_secondary_color: str = "#9ca3af"
    bar_color_high: str = "#10b981"    # Green (> 50%)
    bar_color_med: str = "#f59e0b"     # Amber (20% - 50%)
    bar_color_low: str = "#ef4444"     # Red (< 20%)
    bar_bg_color: str = "#2d2d38"
    accent_color: str = "#6366f1"
    
    # Position
    window_x: int = -1
    window_y: int = -1
    
    # Model filters & grouping
    group_similar_models: bool = True
    hidden_models: List[str] = field(default_factory=list)
    
    # Manual connection overrides (optional)
    manual_mode: bool = False
    manual_port: int = 0
    manual_token: str = ""


class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, "config.json")
        else:
            self.config_path = config_path
        self.config = self.load()

    def load(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            config = AppConfig()
            self.save(config)
            return config
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter unknown keys to prevent TypeError
            valid_keys = AppConfig.__annotations__.keys()
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return AppConfig(**filtered)
        except Exception:
            return AppConfig()

    def save(self, config: Optional[AppConfig] = None) -> bool:
        if config is not None:
            self.config = config
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
