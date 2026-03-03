"""LaTeX code editor component wrapping NiceGUI's ui.codemirror."""
import json

from nicegui import ui

from src.state import state
from src.utils.config import DEFAULT_LANGUAGE, DEFAULT_THEME_DARK, DEFAULT_THEME_LIGHT


class LatexEditor:
    """LaTeX code editor component."""

    def __init__(self):
        self.editor: ui.codemirror | None = None

    def build(self, container):
        """Build the editor inside the given container."""
        with container:
            self.editor = (
                ui.codemirror(
                    value=state.content,
                    on_change=self._on_change,
                    language=DEFAULT_LANGUAGE,
                    theme=DEFAULT_THEME_DARK,
                    line_wrapping=True,
                    indent="  ",
                )
                .classes("w-full h-full")
                .style("flex: 1; min-height: 0;")
            )
            state.editor_element = self.editor

    def _on_change(self, e):
        """Handle editor content changes."""
        state.content = e.value

    def set_content(self, content: str):
        """Programmatically update editor content via JS dispatch."""
        state.content = content
        if not self.editor:
            return
        # Use CodeMirror's dispatch API directly to reliably replace all content.
        # json.dumps handles all escaping (backslashes, quotes, newlines).
        safe = json.dumps(content)
        ui.run_javascript(f"""
            const el = getElement("{self.editor.id}");
            if (el && el.editor) {{
                const view = el.editor;
                view.dispatch({{
                    changes: {{from: 0, to: view.state.doc.length, insert: {safe}}}
                }});
            }}
        """)

    def set_theme(self, theme: str):
        """Switch CodeMirror theme (e.g. 'vscodeDark' or 'githubLight')."""
        if not self.editor:
            return
        self.editor._props['theme'] = theme
        self.editor.update()

    def insert_at_cursor(self, text: str):
        """Insert text at the current cursor position."""
        if not self.editor:
            return
        safe = json.dumps(text)
        ui.run_javascript(f"""
            const el = getElement("{self.editor.id}");
            if (el && el.editor) {{
                const view = el.editor;
                const cursor = view.state.selection.main.head;
                view.dispatch({{
                    changes: {{from: cursor, insert: {safe}}}
                }});
            }}
        """)
