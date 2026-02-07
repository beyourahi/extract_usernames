"""Configuration management for Instagram Username Extractor."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages persistent user configuration."""
    
    CONFIG_DIR = Path.home() / ".config" / "extract-usernames"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    
    DEFAULT_CONFIG = {
        "input_dir": str(Path.home() / "Desktop" / "screenshots"),
        "output_dir": str(Path.home() / "Desktop" / "leads"),
        "vlm_enabled": True,
        "vlm_model": "glm-ocr:bf16",
        "diagnostics": False,
        "workers": None,  # Auto-detect
        "notion": {
            "enabled": False,
            "token": "",
            "database_id": "",
            "validation_delay": 2.0,
            "skip_validation": False,
            "auto_sync": False,
        }
    }
    
    def __init__(self):
        """Initialize config manager."""
        self.config_dir = self.CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_file.exists()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.exists():
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Merge with defaults to handle new config keys
            merged = self.DEFAULT_CONFIG.copy()
            self._deep_merge(merged, config)
            return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error loading config: {e}")
            print(f"⚠️  Using default configuration")
            return self.DEFAULT_CONFIG.copy()
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            self._ensure_config_dir()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except IOError as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """Update specific config values."""
        config = self.load()
        self._deep_merge(config, updates)
        return self.save(config)
    
    def reset(self) -> bool:
        """Reset configuration to defaults."""
        return self.save(self.DEFAULT_CONFIG.copy())
    
    def delete(self) -> bool:
        """Delete configuration file."""
        try:
            if self.exists():
                self.config_file.unlink()
            return True
        except IOError as e:
            print(f"❌ Error deleting config: {e}")
            return False
    
    def _deep_merge(self, base: Dict, updates: Dict):
        """Deep merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get_config_path(self) -> str:
        """Get config file path as string."""
        return str(self.config_file)
    
    def display(self, config: Optional[Dict[str, Any]] = None):
        """Display current configuration."""
        if config is None:
            config = self.load()
        
        print("\n" + "=" * 60)
        print("Current Configuration")
        print("=" * 60)
        print(f"Input Directory:  {config['input_dir']}")
        print(f"Output Directory: {config['output_dir']}")
        print(f"VLM Mode:         {'Enabled' if config['vlm_enabled'] else 'Disabled'}")
        if config['vlm_enabled']:
            print(f"VLM Model:        {config['vlm_model']}")
        print(f"Diagnostics:      {'Enabled' if config['diagnostics'] else 'Disabled'}")
        print(f"\nNotion Integration: {'Enabled' if config['notion']['enabled'] else 'Disabled'}")
        if config['notion']['enabled']:
            token_preview = config['notion']['token'][:10] + "..." if config['notion']['token'] else "(not set)"
            db_preview = config['notion']['database_id'][:8] + "..." if config['notion']['database_id'] else "(not set)"
            print(f"  Token:          {token_preview}")
            print(f"  Database ID:    {db_preview}")
            print(f"  Auto-sync:      {'Yes' if config['notion'].get('auto_sync', False) else 'No'}")
            print(f"  Validation:     {'Skip' if config['notion']['skip_validation'] else 'Enabled'}")
        print("=" * 60 + "\n")
