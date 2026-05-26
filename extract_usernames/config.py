"""Persistent JSON config for the CLI.

Single source of truth: `~/.config/extract-usernames/config.json` (XDG-style,
not platform-aware — Windows users get `C:\\Users\\<u>\\.config\\...`).
Schema is the flat top-level keys + nested `notion` block in `DEFAULT_CONFIG`.

Invariant: `load()` deep-merges file contents into `DEFAULT_CONFIG`, so adding
new keys to `DEFAULT_CONFIG` is backwards-compatible without a migration step.
There is no schema version field — see CLAUDE.md "Config versioning" warning.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Side-effecting config store. `__init__` creates the config directory."""

    CONFIG_DIR = Path.home() / ".config" / "extract-usernames"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    # Notion token is stored in plaintext — acceptable for a personal lead-gen
    # CLI but should never be checked in or shipped in container images.
    # `workers: None` means auto-detect in extractor.detect_hardware().
    DEFAULT_CONFIG = {
        "input_dir": str(Path.home() / "Desktop" / "screenshots"),
        "output_dir": str(Path.home() / "Desktop" / "leads"),
        "vlm_enabled": True,
        "vlm_model": "glm-ocr:bf16",
        "diagnostics": False,
        "workers": None,
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
        # Side effect: `mkdir(parents=True, exist_ok=True)` creates CONFIG_DIR
        # eagerly so callers can `display()`/`get_config_path()` without first
        # calling `save()`.
        self.config_dir = self.CONFIG_DIR
        self.config_file = self.CONFIG_FILE
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.config_file.exists()

    def load(self) -> Dict[str, Any]:
        """Return merged config dict. On parse/IO failure, returns DEFAULT_CONFIG copy.

        Failure mode: corrupt JSON prints a warning to stdout and silently falls
        back to defaults — does NOT raise. Callers cannot distinguish "no config"
        from "broken config" without separately checking `exists()`.
        """
        if not self.exists():
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Deep-merge ensures keys added to DEFAULT_CONFIG in future versions
            # are present in returned dict even if absent from on-disk file.
            merged = self.DEFAULT_CONFIG.copy()
            self._deep_merge(merged, config)
            return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error loading config: {e}")
            print(f"⚠️  Using default configuration")
            return self.DEFAULT_CONFIG.copy()

    def save(self, config: Dict[str, Any]) -> bool:
        """Overwrites CONFIG_FILE atomically-ish (no temp-file swap). Returns success bool."""
        try:
            self._ensure_config_dir()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except IOError as e:
            print(f"❌ Error saving config: {e}")
            return False

    def update(self, updates: Dict[str, Any]) -> bool:
        """Load → deep-merge `updates` → save. NOT a partial PATCH at disk level."""
        config = self.load()
        self._deep_merge(config, updates)
        return self.save(config)

    def reset(self) -> bool:
        return self.save(self.DEFAULT_CONFIG.copy())

    def delete(self) -> bool:
        try:
            if self.exists():
                self.config_file.unlink()
            return True
        except IOError as e:
            print(f"❌ Error deleting config: {e}")
            return False

    def _deep_merge(self, base: Dict, updates: Dict):
        """In-place recursive merge of `updates` into `base`. Lists are replaced, not merged."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get_config_path(self) -> str:
        return str(self.config_file)

    def display(self, config: Optional[Dict[str, Any]] = None):
        """Pretty-print config to stdout. Notion token/db_id are truncated previews,
        never the full secret — safe to include in bug reports."""
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
