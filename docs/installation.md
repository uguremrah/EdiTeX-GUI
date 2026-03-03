# EdiTeX-GUI -- Windows Installation Guide

Step-by-step instructions for installing and running EdiTeX-GUI on Windows 10/11.

## Prerequisites

You need three things installed before starting:

1. **Python 3.13+**
2. **uv** (Python package manager)
3. **MiKTeX** (LaTeX distribution)

If you already have all three, skip to [Clone and Install](#3-clone-and-install).

---

## 1. Install Python 3.13+

### Option A: Official installer (recommended)

1. Download the latest Python 3.13 installer from [python.org/downloads](https://www.python.org/downloads/).
2. Run the installer. **Check "Add python.exe to PATH"** at the bottom of the first screen.
3. Click **Install Now**.
4. Verify in a terminal:

```powershell
python --version
# Python 3.13.x
```

### Option B: Via winget

```powershell
winget install Python.Python.3.13
```

Close and reopen your terminal after installation.

---

## 2. Install uv (Package Manager)

`uv` is a fast Python package manager that replaces pip and virtualenv. EdiTeX-GUI uses it to manage dependencies and run the application.

### Option A: Official installer (recommended)

Open PowerShell and run:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### Option B: Via pip

```powershell
pip install uv
```

### Option C: Via winget

```powershell
winget install astral-sh.uv
```

Verify the installation:

```powershell
uv --version
# uv 0.9.x
```

> **Note:** If `uv` is not found after installation, close and reopen your terminal. The installer adds `%USERPROFILE%\.local\bin` to your PATH.

---

## 3. Install MiKTeX (LaTeX Distribution)

MiKTeX provides `pdflatex`, `bibtex`, `synctex`, and all LaTeX packages needed for compilation.

1. Download the MiKTeX installer from [miktex.org/download](https://miktex.org/download).
2. Run the installer. Choose **"Install for current user"** unless you need system-wide access.
3. During installation, set **"Install missing packages on-the-fly"** to **Yes** (this allows MiKTeX to automatically download LaTeX packages when a document needs them).
4. Verify in a terminal:

```powershell
pdflatex --version
# MiKTeX-pdfTeX ... (MiKTeX 24.x)
```

### Default installation path

MiKTeX installs its binaries to:

```
C:\Users\<username>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\
```

EdiTeX-GUI is configured for this default path. If you installed MiKTeX elsewhere, update `MIKTEX_BIN_DIR` in `src/utils/config.py` (see [Configuration](#6-configuration) below).

---

## 4. Clone and Install

Open a terminal (PowerShell, Command Prompt, or Git Bash) and run:

```bash
# Clone the repository
git clone https://github.com/ugureren/editex-gui.git
cd editex-gui

# Install all dependencies into a virtual environment
uv sync
```

`uv sync` will:
- Create a `.venv/` virtual environment in the project directory
- Install all dependencies from `pyproject.toml` (NiceGUI, PyMuPDF, FastMCP, httpx, bibtexparser, watchfiles)
- Lock versions in `uv.lock` for reproducible builds

To also install development/test dependencies:

```bash
uv sync --extra dev
```

---

## 5. Run EdiTeX-GUI

### Start the editor

```bash
uv run python -m src.app
```

This will:
1. Start the NiceGUI web server on `http://127.0.0.1:8080`
2. Automatically open your default browser to the editor

### Desktop shortcut (optional)

A `launch.bat` file is included in the repository root. To create a desktop shortcut:

1. Right-click `launch.bat` in File Explorer
2. Select **Send to > Desktop (create shortcut)**
3. Rename the shortcut to "EdiTeX-GUI"

Or run this PowerShell command to create one automatically:

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\EdiTeX-GUI.lnk")
$Shortcut.TargetPath = "$PWD\launch.bat"
$Shortcut.WorkingDirectory = "$PWD"
$Shortcut.Description = "Launch EdiTeX-GUI LaTeX Editor"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
```

### Verify it works

1. Click **New** in the toolbar to create a project
2. Type some LaTeX in the editor
3. Click **Compile** (or press `Ctrl+B`)
4. You should see the PDF preview appear on the right

---

## 6. Configuration

All configurable values are in `src/utils/config.py`:

| Constant | Default | Description |
|---|---|---|
| `MIKTEX_BIN_DIR` | `C:\Users\<user>\AppData\Local\Programs\MiKTeX\miktex\bin\x64` | Path to MiKTeX binaries |
| `PDFLATEX_PATH` | `<MIKTEX_BIN_DIR>\pdflatex.exe` | pdflatex executable |
| `LATEX_PATH` | `<MIKTEX_BIN_DIR>\latex.exe` | latex executable (DVI output) |
| `BIBTEX_PATH` | `<MIKTEX_BIN_DIR>\bibtex.exe` | bibtex executable |
| `SYNCTEX_PATH` | `<MIKTEX_BIN_DIR>\synctex.exe` | SyncTeX executable |
| `APP_HOST` | `127.0.0.1` | Server bind address |
| `APP_PORT` | `8080` | Server port |
| `DEFAULT_PROJECT_DIR` | `~/latex-projects` | Where new projects are created |
| `PDF_RENDER_DPI_SCALE` | `2.0` | PDF render quality (2x = retina) |

### Using TeX Live instead of MiKTeX

If you use TeX Live, update `MIKTEX_BIN_DIR` in `src/utils/config.py` to point to your TeX Live `bin/` directory:

```python
MIKTEX_BIN_DIR = Path(r"C:\texlive\2025\bin\windows")
```

The rest of the executable names (`pdflatex.exe`, `bibtex.exe`, `synctex.exe`) are the same for TeX Live.

---

## 7. Set Up MCP Server (Claude Code Integration)

The MCP server lets Claude Code read, edit, and compile your LaTeX documents through AI-powered tools. This step is **optional** -- the editor works fine without it.

### Prerequisites for MCP

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- EdiTeX-GUI application running (`uv run python -m src.app`)

### Register the MCP server

Add the following to your MCP configuration file at `~/.mcp.json` (create it if it doesn't exist):

```json
{
  "mcpServers": {
    "editex": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "C:\\Users\\<username>\\path\\to\\editex-gui",
        "python", "-m", "src.mcp"
      ],
      "env": {}
    }
  }
}
```

**Important:** Replace `C:\\Users\\<username>\\path\\to\\editex-gui` with the actual absolute path to where you cloned the repository. Use double backslashes on Windows.

### Why `--directory` and not `--project`?

The `--directory` flag changes the working directory **and** activates the project's virtual environment. The `--project` flag only sets the venv without changing the CWD, which means `python -m src.mcp` can't find the `src` package. Always use `--directory`.

### Verify the MCP connection

1. Start the EdiTeX-GUI application: `uv run python -m src.app`
2. Open a new Claude Code session
3. The green **MCP** indicator in the editor's header bar should appear
4. In Claude Code, you can now ask:
   - "Read my LaTeX document"
   - "Compile my paper and show me any errors"
   - "Add a new section called Related Work"
   - "Show me the document structure"

### Available MCP tools

| Tool | Description |
|---|---|
| `get_document_content` | Read the current LaTeX source from the editor |
| `update_document_content` | Replace the entire document content |
| `compile_document` | Save and compile (returns errors/warnings) |
| `get_compilation_errors` | Retrieve the latest compilation results |
| `get_document_structure` | Parse sections, labels, references, citations, packages |
| `search_replace` | Find and replace text (literal or regex) |
| `insert_at_position` | Insert text at a specific line number |
| `get_project_info` | Get file path, project directory, compilation status |
| `list_project_files` | List all files in the project directory |
| `read_file` | Read any file in the project (`.bib`, `.sty`, etc.) |

---

## 8. Running Tests

Install dev dependencies and run the test suite:

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

Expected output: **72 tests passing** covering the LaTeX parser, compiler log parsing, and API logic.

---

## 9. Updating

To update to the latest version:

```bash
cd editex-gui
git pull
uv sync
```

---

## Troubleshooting

### "pdflatex not found" or compilation fails

- Verify MiKTeX is installed: `pdflatex --version`
- If installed to a non-default location, update `MIKTEX_BIN_DIR` in `src/utils/config.py`
- Make sure MiKTeX's bin directory is in your system PATH, or rely on the absolute path in config

### Port 8080 already in use

Change `APP_PORT` in `src/utils/config.py` to another port (e.g., `8081`). If using MCP, also update the `API_BASE_URL` and the bridge's base URL in `src/mcp/bridge.py`.

### "Module not found: src" when running MCP server

Make sure your `.mcp.json` uses `--directory` (not `--project`):

```json
"args": ["run", "--directory", "C:\\path\\to\\editex-gui", "python", "-m", "src.mcp"]
```

### MCP indicator shows red

- Make sure the EdiTeX-GUI app is running **before** starting Claude Code
- Check that `http://localhost:8080/api/health` returns a 200 response in your browser

### uv not found

Close and reopen your terminal. If still not found, check that `%USERPROFILE%\.local\bin` is in your PATH:

```powershell
$env:PATH -split ";" | Select-String ".local"
```

### Python version mismatch

EdiTeX-GUI requires Python 3.13+. Check your version:

```bash
python --version
```

If you have multiple Python versions, `uv` will use the one specified in `.python-version` (3.13).
