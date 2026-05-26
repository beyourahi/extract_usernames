"""Public package surface.

Re-exports only `ConfigManager` and `__version__`. All extraction logic lives in
`_archive.extract_usernames` (module-level globals: `VLM_MODEL`, `OUTPUT_DIR`,
`VERIFIED_FILE`, etc.) and is invoked via `main.run_extraction`. CLI entry point
is `cli:main` (declared in `pyproject.toml [project.scripts]`).
"""

__version__ = "2.0.0"
__author__ = "Rahi Khan"
__email__ = "beyourahi@gmail.com"

from .config import ConfigManager

__all__ = ["ConfigManager", "__version__"]
