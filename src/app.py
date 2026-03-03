"""Main NiceGUI application for EdiTeX-GUI."""
import logging
from pathlib import Path

from nicegui import app, ui

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from src.api import api_router
from src.editor.compiler import compile_latex
from src.editor.component import LatexEditor
from src.editor.file_manager import (
    create_new_project,
    open_file,
    save_file,
)
from src.editor.pdf_viewer import PdfViewer
from src.editor.synctex import forward_search
from src.panels.bibliography import BibliographyPanel
from src.panels.errors import ErrorPanel
from src.panels.figures import FigurePanel
from src.panels.templates import TemplatePanel
from src.state import add_recent_file, load_recent_files, state
from src.utils.config import (
    APP_HOST,
    APP_PORT,
    DEFAULT_PROJECT_DIR,
    DEFAULT_THEME_DARK,
    DEFAULT_THEME_LIGHT,
)

# Register internal API endpoints for MCP bridge
app.include_router(api_router)

# Global component references
latex_editor = LatexEditor()
pdf_viewer = PdfViewer()
error_panel = ErrorPanel()
figure_panel = FigurePanel()
bibliography_panel = BibliographyPanel()
template_panel = TemplatePanel()

# Wire up editor references so panels can insert text
figure_panel.set_editor(latex_editor)
bibliography_panel.set_editor(latex_editor)
template_panel.set_editor(latex_editor)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

async def do_compile():
    """Save and compile the current document."""
    logger = logging.getLogger("app.compile")
    try:
        logger.info("do_compile called, file_path=%s, content_len=%d",
                     state.file_path, len(state.content))
        if state.file_path is None:
            ui.notify("No file open. Create or open a project first.", type="warning")
            return

        save_file(state.content)
        state.last_saved_content = state.content
        logger.info("File saved to %s (%d bytes)", state.file_path, len(state.content))
        ui.notify("Compiling...", type="info", timeout=2000)
        await error_panel.refresh()

        success = await compile_latex(state.file_path)
        logger.info("Compilation result: success=%s, pdf_path=%s", success, state.pdf_path)

        if success:
            state.current_page = 0
            await pdf_viewer.refresh()
            ui.notify("Compilation successful", type="positive")
        else:
            ui.notify("Compilation failed - see errors below", type="negative")

        await error_panel.refresh()
    except Exception:
        logger.exception("do_compile crashed")
        ui.notify("Internal error during compilation - check logs", type="negative")


async def do_save():
    """Save the current document."""
    if state.file_path is None:
        ui.notify("No file open", type="warning")
        return
    save_file(state.content)
    state.last_saved_content = state.content
    ui.notify("Saved", type="positive", timeout=1000)


async def auto_save():
    """Auto-save if the file has changed since the last save."""
    if state.file_path is None:
        return
    if state.content == state.last_saved_content:
        return
    try:
        save_file(state.content)
        state.last_saved_content = state.content
        logging.getLogger("app.autosave").info(
            "Auto-saved %s (%d bytes)", state.file_path, len(state.content)
        )
    except Exception:
        logging.getLogger("app.autosave").exception("Auto-save failed")


async def do_forward_search():
    """Perform SyncTeX forward search from current editor cursor line."""
    if state.file_path is None or state.pdf_path is None:
        return

    # Get the current cursor line from the editor via JS
    if state.editor_element is None:
        return

    editor_id = state.editor_element.id
    line = await ui.run_javascript(f"""
        const el = getElement("{editor_id}");
        if (el && el.editor) {{
            const view = el.editor;
            const pos = view.state.selection.main.head;
            return view.state.doc.lineAt(pos).number;
        }}
        return 1;
    """)

    if not line:
        line = 1

    result = await forward_search(state.file_path, int(line))
    if result:
        # SyncTeX pages are 1-based, state.current_page is 0-based
        target_page = result["page"] - 1
        if 0 <= target_page < state.total_pages:
            state.current_page = target_page
            await pdf_viewer.refresh()
            ui.notify(
                f"Jumped to page {result['page']}",
                type="info",
                timeout=1500,
            )
    else:
        ui.notify("SyncTeX: could not find PDF location", type="warning", timeout=2000)


async def do_new_project():
    """Create a new LaTeX project via dialog."""
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("New Project").classes("text-lg font-bold")
        ui.separator()
        name_input = ui.input(
            "Project name", value="my-paper"
        ).classes("w-full").props('outlined dense')
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Create", on_click=lambda: _create_project(name_input, dialog)).props(
                "color=primary"
            )
    dialog.open()


async def _create_project(name_input, dialog):
    name = name_input.value.strip()
    if not name:
        ui.notify("Enter a project name", type="warning")
        return
    create_new_project(name)
    latex_editor.set_content(state.content)
    state.last_saved_content = state.content
    ui.notify(f"Project '{name}' created", type="positive")
    dialog.close()
    await _refresh_side_panels()


async def do_open_file():
    """Open a .tex file via a browsable file tree dialog."""
    current_dir_holder = {"path": Path.home()}
    recents = load_recent_files()

    with ui.dialog() as dialog, ui.card().classes("w-[650px]"):
        ui.label("Open File").classes("text-lg font-bold")
        ui.separator()

        # ---- Recent files section ----
        if recents:
            with ui.row().classes("w-full items-center gap-1"):
                ui.icon("history", color="blue-5").classes("text-sm")
                ui.label("Recent Files").classes("text-xs font-bold text-gray-500 dark:text-gray-400")
            recent_area = ui.scroll_area().classes("w-full border rounded").style(
                "max-height: 120px;"
            )
            with recent_area:
                for rpath_str in recents:
                    rpath = Path(rpath_str)
                    with ui.row().classes(
                        "w-full items-center gap-2 px-3 py-1 cursor-pointer "
                        "hover:bg-green-100 dark:hover:bg-green-900 rounded"
                    ) as rrow:
                        ui.icon("description", color="green-7").classes("text-lg")
                        with ui.column().classes("gap-0 min-w-0 flex-grow"):
                            ui.label(rpath.name).classes(
                                "text-sm font-medium text-green-800 dark:text-green-300"
                            )
                            ui.label(str(rpath.parent)).classes(
                                "text-[10px] text-gray-400 truncate"
                            ).style("max-width: 500px;")
                        rrow.on("click", lambda p=rpath: _open_and_close(p, dialog))
            ui.separator().classes("my-1")

        # ---- Browse section ----
        with ui.row().classes("w-full items-center gap-1"):
            ui.icon("folder_open", color="amber-7").classes("text-sm")
            ui.label("Browse").classes("text-xs font-bold text-gray-500 dark:text-gray-400")

        # Breadcrumb / current path display
        path_display = ui.label(str(current_dir_holder["path"])).classes(
            "text-xs text-gray-500 font-mono break-all"
        )

        # Navigation row
        with ui.row().classes("w-full items-center gap-1"):
            ui.button(
                icon="arrow_upward",
                on_click=lambda: _browse_dir(
                    current_dir_holder["path"].parent,
                    current_dir_holder, path_display, file_list, dialog,
                ),
            ).props("flat dense round").tooltip("Parent directory")
            ui.button(
                icon="home",
                on_click=lambda: _browse_dir(
                    Path.home(), current_dir_holder, path_display, file_list, dialog,
                ),
            ).props("flat dense round").tooltip("Home")
            ui.button(
                icon="desktop_windows",
                on_click=lambda: _browse_dir(
                    Path.home() / "Desktop",
                    current_dir_holder, path_display, file_list, dialog,
                ),
            ).props("flat dense round").tooltip("Desktop")
            if DEFAULT_PROJECT_DIR.exists():
                ui.button(
                    icon="folder_special",
                    on_click=lambda: _browse_dir(
                        DEFAULT_PROJECT_DIR,
                        current_dir_holder, path_display, file_list, dialog,
                    ),
                ).props("flat dense round").tooltip("LaTeX Projects")

        # File listing (shorter if recents take space)
        browse_height = "280px" if recents else "350px"
        file_list = ui.scroll_area().classes("w-full border rounded").style(
            f"height: {browse_height};"
        )

        # Manual path input
        with ui.row().classes("w-full items-end gap-2 mt-2"):
            path_input = ui.input(
                "Or paste full path:", value=""
            ).classes("flex-grow").props("outlined dense")
            ui.button(
                "Open", on_click=lambda: _open_path_input(path_input, dialog)
            ).props("color=primary dense")

        with ui.row().classes("w-full justify-end mt-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")

        # Populate initial listing
        _browse_dir(
            current_dir_holder["path"],
            current_dir_holder, path_display, file_list, dialog,
        )

    dialog.open()


def _browse_dir(target: Path, holder: dict, path_label, file_list, dialog):
    """Populate the file list for the given directory."""
    try:
        target = target.resolve()
        if not target.is_dir():
            return
    except (OSError, PermissionError):
        ui.notify("Cannot access that directory", type="warning")
        return

    holder["path"] = target
    path_label.text = str(target)

    file_list.clear()
    with file_list:
        try:
            entries = sorted(
                target.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            ui.label("Permission denied").classes("text-red-500 p-4")
            return

        # Show drives on Windows when at root
        if str(target) == target.anchor:
            for drive_letter in "CDEFGHIJ":
                dp = Path(f"{drive_letter}:/")
                if dp.exists():
                    with ui.row().classes(
                        "w-full items-center gap-2 px-3 py-1 cursor-pointer "
                        "hover:bg-blue-100 dark:hover:bg-blue-900 rounded"
                    ) as row:
                        ui.icon("storage", color="amber-8").classes("text-lg")
                        ui.label(f"{drive_letter}:\\").classes("font-mono")
                        row.on(
                            "click",
                            lambda d=dp: _browse_dir(
                                d, holder, path_label, file_list, dialog,
                            ),
                        )

        for entry in entries:
            try:
                name = entry.name
            except (OSError, PermissionError):
                continue
            # Skip hidden/system entries
            if name.startswith(".") or name.startswith("$"):
                continue

            if entry.is_dir():
                with ui.row().classes(
                    "w-full items-center gap-2 px-3 py-1 cursor-pointer "
                    "hover:bg-blue-100 dark:hover:bg-blue-900 rounded"
                ) as row:
                    ui.icon("folder", color="amber-8").classes("text-lg")
                    ui.label(name).classes("text-sm")
                    row.on(
                        "click",
                        lambda p=entry: _browse_dir(
                            p, holder, path_label, file_list, dialog,
                        ),
                    )
            elif entry.suffix.lower() == ".tex":
                with ui.row().classes(
                    "w-full items-center gap-2 px-3 py-1 cursor-pointer "
                    "hover:bg-green-100 dark:hover:bg-green-900 rounded"
                ) as row:
                    ui.icon("description", color="green-7").classes("text-lg")
                    ui.label(name).classes("text-sm font-medium text-green-800 dark:text-green-300")
                    row.on(
                        "click",
                        lambda p=entry: _open_and_close(p, dialog),
                    )


async def _refresh_side_panels():
    """Refresh all side panels after opening/creating a project."""
    await figure_panel.refresh()
    await bibliography_panel.refresh()
    await template_panel.refresh()


async def _open_and_close(path: Path, dialog):
    content = open_file(path)
    latex_editor.set_content(content)
    state.last_saved_content = content
    add_recent_file(path)
    ui.notify(f"Opened {path.name}", type="positive")
    dialog.close()
    await _refresh_side_panels()


async def _open_path_input(path_input, dialog):
    p = Path(path_input.value.strip())
    if p.exists() and p.suffix == ".tex":
        await _open_and_close(p, dialog)
    elif p.exists() and p.is_dir():
        ui.notify("That's a directory, not a .tex file", type="warning")
    else:
        ui.notify("File not found or not a .tex file", type="warning")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

@ui.page("/")
async def main_page():
    """Main editor page layout."""

    # Full-viewport layout with no scrollbar, panels fill height
    ui.add_head_html("""
    <style>
        html, body { height: 100%; margin: 0; overflow: hidden; }
        .nicegui-content { height: 100vh; display: flex; flex-direction: column; }
        .q-page { min-height: 0 !important; flex: 1; display: flex; flex-direction: column; }
        .q-page-container { flex: 1; display: flex; flex-direction: column; }
        .q-splitter__separator { background: #374151 !important; }
        /* Make splitter panels fill height */
        .q-splitter__panel { display: flex !important; flex-direction: column !important; }
        /* Make CodeMirror fill its container */
        .cm-editor { height: 100% !important; }
        .cm-editor .cm-scroller { overflow: auto !important; }
        /* Right sidebar tab panels fill available space */
        .right-sidebar .q-tab-panel { padding: 0 !important; }
        .right-sidebar .q-tab-panels { flex: 1; min-height: 0; overflow-y: auto; }
        /* Header tabs styling */
        .header-tabs .q-tab { color: rgba(255,255,255,0.7) !important; min-height: 36px !important; padding: 0 12px !important; }
        .header-tabs .q-tab--active { color: #10b981 !important; }
        .header-tabs .q-tab__indicator { background: #10b981 !important; }
        .header-tabs { min-height: 36px !important; }
        .header-tabs .q-tabs__arrow { display: none !important; }
    </style>
    """)

    # ---- HEADER / TOOLBAR ----
    with ui.header().classes(
        "bg-gray-900 text-white items-center gap-3 px-5 py-2"
    ).style("border-bottom: 2px solid #10b981;"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("article", color="green-4").classes("text-2xl")
            ui.label("EdiTeX-GUI").classes("text-lg font-bold tracking-wide")

        ui.separator().props("vertical inset").classes("mx-1 opacity-30")

        ui.button("New", icon="add", on_click=do_new_project).props(
            "flat color=white dense no-caps"
        )
        ui.button("Open", icon="folder_open", on_click=do_open_file).props(
            "flat color=white dense no-caps"
        )
        ui.button("Save", icon="save", on_click=do_save).props(
            "flat color=white dense no-caps"
        ).tooltip("Ctrl+S")

        ui.separator().props("vertical inset").classes("mx-1 opacity-30")

        ui.button("Compile", icon="play_arrow", on_click=do_compile).props(
            "color=green dense no-caps"
        ).classes("px-4").tooltip("Ctrl+B")

        # Export format toggle (PDF/DVI)
        with ui.button_group().props("dense rounded"):
            pdf_fmt_btn = ui.button("PDF", on_click=lambda: _set_format("pdf", pdf_fmt_btn, dvi_fmt_btn)).props(
                "dense no-caps color=green size=sm"
            ).classes("px-2")
            dvi_fmt_btn = ui.button("DVI", on_click=lambda: _set_format("dvi", dvi_fmt_btn, pdf_fmt_btn)).props(
                "dense no-caps flat color=white size=sm"
            ).classes("px-2")

        def _set_format(fmt, active_btn, inactive_btn):
            state.export_format = fmt
            active_btn.props(remove="flat", add="color=green")
            inactive_btn.props(remove="color=green", add="flat color=white")

        ui.button(
            "SyncTeX", icon="sync", on_click=do_forward_search
        ).props("flat color=white dense no-caps").tooltip("Ctrl+Click: Jump to PDF")

        # Dark/light theme toggle
        dark_mode_toggle = ui.dark_mode(state.dark_mode)

        async def do_toggle_theme():
            state.dark_mode = not state.dark_mode
            if state.dark_mode:
                dark_mode_toggle.enable()
                latex_editor.set_theme(DEFAULT_THEME_DARK)
                theme_btn.props("icon=dark_mode")
                theme_btn.tooltip("Switch to light theme")
            else:
                dark_mode_toggle.disable()
                latex_editor.set_theme(DEFAULT_THEME_LIGHT)
                theme_btn.props("icon=light_mode")
                theme_btn.tooltip("Switch to dark theme")

        theme_btn = ui.button(
            icon="dark_mode", on_click=do_toggle_theme
        ).props("flat color=white dense round").tooltip("Switch to light theme")

        ui.separator().props("vertical inset").classes("mx-1 opacity-30")

        # MCP connectivity indicator
        with ui.row().classes("items-center gap-1"):
            mcp_dot = ui.icon("circle", color="green-5").classes("text-[8px]")
            mcp_label = ui.label("MCP").classes("text-xs text-green-400")
            mcp_dot.tooltip("MCP API available")

        async def check_mcp_health():
            import httpx
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    r = await client.get("http://localhost:8080/api/health")
                    if r.status_code == 200:
                        mcp_dot.props("color=green-5")
                        mcp_label.classes(replace="text-xs text-green-400")
                    else:
                        mcp_dot.props("color=red-5")
                        mcp_label.classes(replace="text-xs text-red-400")
            except Exception:
                mcp_dot.props("color=red-5")
                mcp_label.classes(replace="text-xs text-red-400")

        ui.timer(10, check_mcp_health)
        ui.timer(1, check_mcp_health, once=True)

        ui.space()

        # Right panel tab selector - centered over the right panel
        with ui.tabs().props("dense no-caps").classes(
            "header-tabs"
        ) as right_tabs:
            pdf_tab = ui.tab("PDF", icon="picture_as_pdf")
            figures_tab = ui.tab("Figures", icon="image")
            bib_tab = ui.tab("Bib", icon="menu_book")
            templates_tab = ui.tab("Templates", icon="library_books")

        ui.space()

        with ui.row().classes("items-center gap-1"):
            ui.icon("edit_note", color="gray-4").classes("text-sm")
            file_label = ui.label("No file open").classes(
                "text-sm text-gray-400 font-mono"
            )
            ui.timer(
                1.0,
                lambda: file_label.set_text(
                    str(state.file_path.name) if state.file_path else "No file open"
                ),
            )

    # ---- MAIN CONTENT: fills all remaining height ----
    # Outer vertical splitter: top = editor+preview, bottom = error panel
    with ui.splitter(value=85, horizontal=True).classes("w-full").style(
        "flex: 1; min-height: 0;"
    ) as vsplit:

        # ---- TOP: editor + right panel ----
        with vsplit.before:
            with ui.splitter(value=50).classes("w-full h-full").style(
                "min-height: 0;"
            ) as hsplit:
                # ---- LEFT: Code Editor ----
                with hsplit.before:
                    editor_container = ui.column().classes(
                        "w-full h-full p-0 m-0"
                    ).style("overflow: hidden;")
                    latex_editor.build(editor_container)

                # ---- RIGHT: Tab panels controlled by header tabs ----
                with hsplit.after:
                    with ui.column().classes(
                        "w-full h-full p-0 m-0 right-sidebar"
                    ).style("overflow: hidden; display: flex; flex-direction: column;"):

                        with ui.tab_panels(right_tabs, value=pdf_tab).classes(
                            "w-full"
                        ).style("flex: 1; min-height: 0;"):

                            # PDF tab
                            with ui.tab_panel(pdf_tab).classes("p-0 m-0").style(
                                "height: 100%; display: flex; flex-direction: column;"
                            ):
                                pdf_container = ui.column().classes(
                                    "w-full h-full p-0 m-0"
                                ).style("background: #f8fafc; overflow: hidden;")
                                pdf_viewer.build(pdf_container)

                            # Figures tab
                            with ui.tab_panel(figures_tab).style(
                                "height: 100%; overflow-y: auto;"
                            ):
                                fig_container = ui.column().classes("w-full")
                                figure_panel.build(fig_container)

                            # Bibliography tab
                            with ui.tab_panel(bib_tab).style(
                                "height: 100%; overflow-y: auto;"
                            ):
                                bib_container = ui.column().classes("w-full")
                                bibliography_panel.build(bib_container)

                            # Templates tab
                            with ui.tab_panel(templates_tab).style(
                                "height: 100%; overflow-y: auto;"
                            ):
                                tmpl_container = ui.column().classes("w-full")
                                template_panel.build(tmpl_container)

        # ---- BOTTOM: Resizable Compilation Output panel ----
        with vsplit.after:
            with ui.column().classes("w-full h-full p-0 m-0").style(
                "overflow: hidden;"
            ):
                with ui.row().classes(
                    "w-full items-center gap-2 px-3 py-1 bg-gray-100"
                ).style("flex-shrink: 0;"):
                    ui.icon("terminal", color="gray-7").classes("text-sm")
                    ui.label("Compilation Output").classes(
                        "text-sm font-medium text-gray-700"
                    )
                error_container = (
                    ui.column()
                    .classes("w-full")
                    .style("flex: 1; min-height: 0; overflow-y: auto;")
                )
                error_panel.build(error_container)

    # ---- AUTO-SAVE TIMER (every 30 seconds) ----
    ui.timer(30, auto_save)

    # ---- INITIAL REFRESH of side panels ----
    # Refresh panels so they show current state on load
    async def _initial_panel_refresh():
        await figure_panel.refresh()
        await bibliography_panel.refresh()
        await template_panel.refresh()

    ui.timer(0.5, _initial_panel_refresh, once=True)

    # ---- KEYBOARD SHORTCUTS ----
    async def handle_key(e):
        if e.action.keydown and e.modifiers.ctrl:
            if e.key.name == "s":
                await do_save()
            elif e.key.name == "b":
                await do_compile()

    ui.keyboard(on_key=handle_key, ignore=[])


# Ensure default project directory exists
DEFAULT_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

ui.run(
    title="EdiTeX-GUI",
    host=APP_HOST,
    port=APP_PORT,
    reload=False,
    show=True,
)
