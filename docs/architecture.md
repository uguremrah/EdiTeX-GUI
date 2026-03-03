# EdiTeX-GUI Architecture

This document describes the internal architecture of EdiTeX-GUI, covering the two-process design, module responsibilities, data flow, and extension points.

## High-Level Overview

EdiTeX-GUI consists of two cooperating processes:

1. **NiceGUI Application** -- the main process serving the web UI on `localhost:8080` and exposing a REST API.
2. **MCP Server** -- a separate process started by Claude Code over stdio, which bridges tool calls to the NiceGUI REST API via HTTP.

```
+-----------------------+         +---------------------------+
|     User's Browser    |         |       Claude Code         |
|  http://localhost:8080|         |     (AI Assistant)        |
+-----------+-----------+         +------------+--------------+
            |                                  |
            | WebSocket (NiceGUI)              | stdio (JSON-RPC / MCP)
            v                                  v
+-----------+----------------------------------+--------------+
|                   NiceGUI Application (Process 1)           |
|                                                             |
|  +------------------+    +------------------------------+   |
|  |   Web UI Layer   |    |   FastAPI REST API (/api/*)  |   |
|  |                  |    |                              |   |
|  |  - CodeMirror    |    |  GET  /api/document          |   |
|  |  - PDF Viewer    |    |  POST /api/document          |   |
|  |  - Error Panel   |    |  POST /api/compile           |   |
|  |  - Figure Panel  |    |  GET  /api/errors            |   |
|  |  - Bib Panel     |    |  GET  /api/structure         |   |
|  |  - Template Panel|    |  POST /api/search-replace    |   |
|  +--------+---------+    |  POST /api/insert-at-line    |   |
|           |              |  GET  /api/project-info       |   |
|           v              |  GET  /api/project-files      |   |
|  +--------+---------+    |  GET  /api/read-file          |   |
|  |  Editor Services  |    |  GET  /api/health             |   |
|  |                  |    +----------+-------------------+   |
|  |  - Compiler      |               |                       |
|  |  - File Manager  |               | HTTP (httpx)          |
|  |  - SyncTeX       |               v                       |
|  |  - LaTeX Parser  |    +----------+-------------------+   |
|  +--------+---------+    |   MCP Server (Process 2)     |   |
|           |              |                              |   |
|           v              |   FastMCP with 10 tools      |   |
|  +--------+---------+    |   EditorBridge (httpx)       |   |
|  |   Global State    |    +------------------------------+   |
|  |  (EditorState)   |                                       |
|  +------------------+                                       |
+-------------------------------------------------------------+
```

## Module Dependency Graph

```
src/app.py ─────────────────────────── Main UI entry point
├── src/state.py ──────────────────── Global EditorState singleton
├── src/api.py ────────────────────── FastAPI REST API
│   ├── src/state.py
│   ├── src/editor/compiler.py
│   ├── src/editor/file_manager.py
│   └── src/utils/latex_parser.py
├── src/editor/
│   ├── compiler.py ───────────────── pdflatex / latex invocation
│   │   ├── src/state.py
│   │   └── src/utils/config.py
│   ├── component.py ──────────────── CodeMirror wrapper
│   │   └── src/state.py
│   ├── file_manager.py ───────────── File I/O (open, save, new project)
│   │   ├── src/state.py
│   │   └── src/utils/config.py
│   ├── pdf_viewer.py ─────────────── PyMuPDF PDF rendering
│   │   ├── src/state.py
│   │   └── src/utils/config.py
│   └── synctex.py ────────────────── SyncTeX forward/inverse search
│       └── src/utils/config.py
├── src/panels/
│   ├── errors.py ─────────────────── Compilation output display
│   │   └── src/state.py
│   ├── figures.py ────────────────── Figure gallery + upload
│   │   └── src/state.py
│   ├── bibliography.py ───────────── Bibliography (.bib) manager
│   │   └── src/state.py
│   └── templates.py ──────────────── Template library
│       ├── src/state.py
│       └── src/editor/file_manager.py
└── src/utils/
    ├── config.py ─────────────────── Paths and constants
    └── latex_parser.py ───────────── Regex-based LaTeX structure parser

src/mcp/ ──────────────────────────── (Separate process)
├── server.py ─────────────────────── FastMCP tool definitions (10 tools)
│   └── bridge.py ─────────────────── httpx client to /api/* endpoints
└── __main__.py ───────────────────── Entry point for `python -m src.mcp`
```

## Core Components

### 1. Global State (`src/state.py`)

All application state lives in a single `EditorState` dataclass instance. Both the UI layer and the API layer read from and write to this shared singleton, which avoids complex message-passing.

| Field Group | Fields | Purpose |
|---|---|---|
| Document | `content`, `file_path`, `project_dir` | Current document and its location on disk |
| Compilation | `is_compiling`, `last_compile_success`, `compile_errors`, `compile_warnings`, `compile_log`, `pdf_path` | Compiler status and results |
| PDF Viewer | `current_page`, `total_pages` | Pagination state |
| Auto-save | `last_saved_content` | Tracks changes since last save |
| Preferences | `dark_mode`, `export_format` | UI settings |
| UI Refs | `editor_element`, `pdf_viewer_element`, `error_panel_element` | NiceGUI element handles (not serializable) |

Recent files are stored separately in `~/.editex-gui/recent_files.json` and managed by `load_recent_files()` / `add_recent_file()`.

### 2. Web UI (`src/app.py`)

The main page is built with NiceGUI components arranged in nested splitters:

```
+------------------------------------------------------------------+
| HEADER: Logo | New Open Save | Compile [PDF|DVI] SyncTeX Theme   |
|              | MCP indicator  |  [PDF] [Figures] [Bib] [Templates]|
+------------------------------------------------------------------+
|                              |                                    |
|  LEFT (50%)                  |  RIGHT (50%)                       |
|  CodeMirror Editor           |  Tab Panels:                       |
|  (LaTeX syntax,              |    - PDF Preview (PyMuPDF)          |
|   vscodeDark/githubLight)    |    - Figure Gallery                 |
|                              |    - Bibliography Manager            |
|                              |    - Template Library                |
+------------------------------------------------------------------+
|  BOTTOM (15%): Compilation Output                                 |
|  [errors in red] [warnings in orange] [clickable line numbers]    |
+------------------------------------------------------------------+
```

**Layout strategy:**
- Outer vertical `ui.splitter(value=85, horizontal=True)` -- editor area (85%) / error panel (15%)
- Inner horizontal `ui.splitter(value=50)` -- code editor (50%) / right panel (50%)
- CSS forces `height: 100vh` with `overflow: hidden` so nothing scrolls at the page level
- CodeMirror fills its container via `flex: 1; min-height: 0` and `.cm-editor { height: 100% }`

**Timers:**
- Auto-save: 30 seconds
- MCP health check: 10 seconds
- File label update: 1 second

### 3. REST API (`src/api.py`)

The API layer is a FastAPI `APIRouter` mounted at `/api`. It is the **single point of truth** for programmatic access -- both the MCP server and (in theory) any external client talk to the editor through these endpoints.

All endpoints read from or write to the global `state` singleton. The compile endpoint additionally invokes `compile_latex()` as an async task.

Path traversal protection is applied on `GET /api/read-file` to prevent reading files outside the project directory.

### 4. Compiler (`src/editor/compiler.py`)

Compilation follows these steps:

1. Determine executable: `pdflatex.exe` for PDF, `latex.exe` for DVI
2. Build args: `--enable-installer -interaction=nonstopmode -synctex=1 -output-directory=<dir>`
3. Run **two passes** via `asyncio.create_subprocess_exec` (second pass resolves cross-references)
4. Parse the log file for errors (regex: `! <message>` followed by `l.<number>`) and warnings (`LaTeX Warning:`, `Package <name> Warning:`)
5. Update `state.compile_errors`, `state.compile_warnings`, `state.compile_log`, `state.pdf_path`

### 5. PDF Viewer (`src/editor/pdf_viewer.py`)

The PDF viewer renders individual pages as PNG images:

1. Open the PDF with PyMuPDF (`fitz.open()`)
2. Render the current page at 2x DPI scale (`page.get_pixmap(matrix=Matrix(scale, scale))`)
3. Store the PNG bytes in a module-level dict keyed by a cache-busting timestamp
4. Serve via `GET /api/pdf-page` FastAPI endpoint
5. Inject an `<img>` tag into the browser DOM via `ui.run_javascript()`

Zoom is implemented by adjusting the `Matrix` scale factor (range 0.25x to 3.0x).

### 6. MCP Server (`src/mcp/`)

The MCP server is a **separate Python process** started by Claude Code:

```
claude code ---> stdio ---> python -m src.mcp ---> FastMCP server
                                                      |
                                                      | httpx (HTTP)
                                                      v
                                              localhost:8080/api/*
```

**Why two processes?** The NiceGUI app must own the event loop and the browser WebSocket connections. The MCP protocol requires a stdio-based process. By bridging over HTTP, the two can run independently.

The `EditorBridge` class (`src/mcp/bridge.py`) wraps all HTTP calls to the REST API. Each MCP tool in `server.py` calls the bridge, formats the response, and returns a string to Claude.

### 7. Panels

| Panel | File | Purpose |
|---|---|---|
| Error Panel | `src/panels/errors.py` | Shows compilation errors (red, clickable) and warnings (orange) |
| Figure Panel | `src/panels/figures.py` | Gallery of project images, drag-drop upload, click to insert `\includegraphics` |
| Bibliography | `src/panels/bibliography.py` | Parse `.bib` files, add entries, click to insert `\cite{key}` |
| Templates | `src/panels/templates.py` | Browse built-in `.tex` templates, create new projects from them |

All panels implement `build(parent)`, `refresh()`, and `set_editor(editor)`. They are refreshed on file open, project creation, and initial page load.

### 8. LaTeX Parser (`src/utils/latex_parser.py`)

A regex-based parser that extracts document structure without a full LaTeX AST:

- **Sections**: `\section`, `\subsection`, etc. (including starred variants)
- **Labels**: `\label{name}`
- **References**: `\ref`, `\eqref`, `\pageref`, `\autoref`
- **Citations**: `\cite{key1,key2}` (with optional arguments)
- **Packages**: `\usepackage[options]{pkg1,pkg2}`

Used by `GET /api/structure` and the MCP `get_document_structure` tool.

## Data Flow Examples

### Compile Flow

```
User clicks [Compile]
  -> do_compile() in app.py
  -> save_file(state.content)
  -> compile_latex(state.file_path)
     -> asyncio.create_subprocess_exec("pdflatex", ...)  (x2 passes)
     -> parse_errors(log), parse_warnings(log)
     -> state.pdf_path = <output>.pdf
  -> pdf_viewer.refresh()
     -> PyMuPDF renders page -> PNG bytes -> /api/pdf-page
  -> error_panel.refresh()
     -> reads state.compile_errors, state.compile_warnings
```

### MCP Tool Call Flow

```
Claude invokes get_document_content()
  -> server.py: mcp tool handler
  -> bridge.get_document() -> httpx GET localhost:8080/api/document
  -> api.py: reads state.content, state.file_path
  -> returns JSON -> bridge formats -> tool returns string to Claude
```

## Extension Points

- **New templates**: Drop `.tex` files into `templates/` -- they appear automatically
- **New MCP tools**: Add `@mcp.tool()` functions in `server.py` + corresponding API endpoint in `api.py`
- **New panels**: Create a class with `build()` / `refresh()` / `set_editor()`, wire it in `app.py`
- **Different compiler**: Change paths in `src/utils/config.py` (e.g., for TeX Live or XeLaTeX)
- **Custom themes**: Add CodeMirror theme names to the theme toggle logic in `app.py`

## Technology Choices

| Decision | Choice | Rationale |
|---|---|---|
| UI framework | NiceGUI | Event-driven (no Streamlit reruns), native CodeMirror support, built-in FastAPI |
| PDF rendering | PyMuPDF -> PNG | Full control over DPI, works cross-browser, enables SyncTeX click coordinates |
| MCP transport | stdio + HTTP bridge | NiceGUI owns the event loop; MCP requires stdio; HTTP cleanly decouples them |
| State management | Singleton dataclass | Simple, no message-passing overhead for a single-user local editor |
| LaTeX parsing | Regex | Sufficient for structure extraction; avoids heavy AST dependencies |
| Recent files | JSON file | Simple persistence, no database needed for a short list |
