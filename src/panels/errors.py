"""Compilation error and warning display panel."""
from nicegui import ui

from src.state import state


class ErrorPanel:
    """Displays compilation errors and warnings."""

    def __init__(self):
        self.container = None

    def build(self, parent):
        with parent:
            self.container = ui.column().classes("w-full p-2 gap-1")

    async def refresh(self):
        """Update the error display from state."""
        if not self.container:
            return
        self.container.clear()
        with self.container:
            if state.is_compiling:
                with ui.row().classes("items-center gap-2"):
                    ui.spinner(size="sm")
                    ui.label("Compiling...").classes("text-blue")
                return

            if state.last_compile_success and not state.compile_errors:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle", color="green")
                    ui.label("Compilation successful").classes("text-green-700")

            for error in state.compile_errors:
                with ui.row().classes(
                    "w-full items-center gap-2 cursor-pointer "
                    "hover:bg-red-50 p-1 rounded"
                ) as row:
                    ui.icon("error", color="red").classes("text-lg")
                    line_num = error.get("line", "?")
                    ui.label(f"Line {line_num}: {error['message']}").classes(
                        "text-red-700"
                    )
                    if isinstance(line_num, int):
                        row.on("click", lambda l=line_num: _jump_to_line(l))

            for warning in state.compile_warnings:
                with ui.row().classes("w-full items-center gap-2 p-1"):
                    ui.icon("warning", color="orange").classes("text-lg")
                    ui.label(warning["message"]).classes("text-orange-700")

            if (
                not state.compile_errors
                and not state.compile_warnings
                and not state.last_compile_success
                and state.compile_log
            ):
                ui.label("See compilation log for details").classes("text-gray-500")


def _jump_to_line(line: int):
    """Jump the editor cursor to a specific line number."""
    if state.editor_element is None:
        return
    editor_id = state.editor_element.id
    ui.run_javascript(f"""
        const view = getElement("{editor_id}").editor;
        const line = view.state.doc.line({line});
        view.dispatch({{
            selection: {{anchor: line.from}},
            scrollIntoView: true,
        }});
        view.focus();
    """)
