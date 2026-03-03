"""Configuration constants for the LaTeX editor."""
from pathlib import Path

# LaTeX compiler paths (MiKTeX)
MIKTEX_BIN_DIR = Path(r"C:\Users\ugure\AppData\Local\Programs\MiKTeX\miktex\bin\x64")
PDFLATEX_PATH = MIKTEX_BIN_DIR / "pdflatex.exe"
LATEX_PATH = MIKTEX_BIN_DIR / "latex.exe"  # DVI output
BIBTEX_PATH = MIKTEX_BIN_DIR / "bibtex.exe"
SYNCTEX_PATH = MIKTEX_BIN_DIR / "synctex.exe"

# App settings
APP_HOST = "127.0.0.1"
APP_PORT = 8080
API_BASE_URL = f"http://localhost:{APP_PORT}/api"

# Default project directory
DEFAULT_PROJECT_DIR = Path.home() / "latex-projects"

# PDF rendering
PDF_RENDER_DPI_SCALE = 2.0  # 2x for retina-quality rendering

# App data directory (persistent settings)
APP_DATA_DIR = Path.home() / ".editex-gui"
RECENT_FILES_PATH = APP_DATA_DIR / "recent_files.json"
MAX_RECENT_FILES = 10

# Editor defaults
DEFAULT_THEME_LIGHT = "githubLight"
DEFAULT_THEME_DARK = "vscodeDark"
DEFAULT_LANGUAGE = "LaTeX"  # NiceGUI CodeMirror supported language literal
