"""Global application state singleton."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.utils.config import APP_DATA_DIR, MAX_RECENT_FILES, RECENT_FILES_PATH

log = logging.getLogger(__name__)


@dataclass
class EditorState:
    """Mutable application state shared between UI and API layer."""

    # Current document
    content: str = ""
    file_path: Path | None = None
    project_dir: Path | None = None

    # Compilation
    is_compiling: bool = False
    last_compile_success: bool = False
    compile_errors: list[dict] = field(default_factory=list)
    compile_warnings: list[dict] = field(default_factory=list)
    compile_log: str = ""
    pdf_path: Path | None = None

    # PDF viewer
    current_page: int = 0
    total_pages: int = 0

    # Auto-save tracking
    last_saved_content: str = ""

    # UI preferences
    dark_mode: bool = True
    export_format: str = "pdf"  # "pdf" or "dvi"

    # UI references (set during UI construction, not serializable)
    editor_element: object | None = None
    pdf_viewer_element: object | None = None
    error_panel_element: object | None = None


def load_recent_files() -> list[str]:
    """Load the recent files list from disk."""
    if not RECENT_FILES_PATH.exists():
        return []
    try:
        data = json.loads(RECENT_FILES_PATH.read_text(encoding="utf-8"))
        return [p for p in data if Path(p).exists()]
    except Exception:
        log.warning("Could not load recent files, starting fresh")
        return []


def add_recent_file(file_path: Path) -> list[str]:
    """Add a file to the recent list and persist. Returns updated list."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    recents = load_recent_files()
    path_str = str(file_path.resolve())
    # Remove if already present, then prepend
    recents = [p for p in recents if p != path_str]
    recents.insert(0, path_str)
    recents = recents[:MAX_RECENT_FILES]
    try:
        RECENT_FILES_PATH.write_text(json.dumps(recents), encoding="utf-8")
    except Exception:
        log.warning("Could not save recent files")
    return recents


# Singleton instance
state = EditorState()
