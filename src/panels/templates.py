"""Template library panel for creating new projects from templates."""
import logging
from pathlib import Path

from nicegui import ui

from src.editor.file_manager import create_new_project
from src.state import state

log = logging.getLogger(__name__)

# Directory where template .tex files are stored
TEMPLATES_DIR = Path(r"C:\Users\ugure\c1\latex-editor\templates")


class TemplatePanel:
    """Panel showing available LaTeX templates for new projects."""

    def __init__(self):
        self.container = None
        self._editor_ref = None
        self._templates_container = None

    def set_editor(self, editor):
        """Store a reference to the LatexEditor for content updates."""
        self._editor_ref = editor

    def build(self, parent):
        """Build the template library UI inside the given container."""
        with parent:
            self.container = ui.column().classes("w-full p-2 gap-2")
            with self.container:
                ui.label("Templates").classes("text-sm font-bold text-gray-600")
                ui.label(
                    "Click a template to create a new project from it."
                ).classes("text-xs text-gray-400")

                self._templates_container = ui.column().classes("w-full gap-2").style(
                    "max-height: 450px; overflow-y: auto;"
                )

    async def refresh(self):
        """Refresh the template list from the templates directory."""
        if self._templates_container is None:
            return

        self._templates_container.clear()

        if not TEMPLATES_DIR.exists():
            with self._templates_container:
                ui.label("Templates directory not found").classes(
                    "text-xs text-gray-400"
                )
            return

        templates = sorted(
            [f for f in TEMPLATES_DIR.iterdir() if f.suffix == ".tex"],
            key=lambda p: p.stem.lower(),
        )

        with self._templates_container:
            if not templates:
                ui.label("No templates available").classes("text-xs text-gray-400")
                return

            for tmpl in templates:
                self._build_template_card(tmpl)

    def _build_template_card(self, tmpl_path: Path):
        """Build a card for a single template."""
        name = tmpl_path.stem
        display_name = name.replace("-", " ").replace("_", " ").title()

        # Read first few lines for a description
        try:
            content = tmpl_path.read_text(encoding="utf-8")
            description = self._extract_description(content, name)
        except Exception:
            content = ""
            description = "LaTeX template"

        # Icon mapping
        icon_map = {
            "basic": "description",
            "ieee": "science",
            "acm": "computer",
            "letter": "mail",
            "arxiv": "cloud_upload",
            "beamer": "slideshow",
            "thesis": "school",
            "report": "summarize",
        }
        icon = icon_map.get(name.lower(), "article")

        with ui.card().classes(
            "w-full cursor-pointer hover:bg-green-50 p-3 transition-colors"
        ).on("click", lambda p=tmpl_path, c=content: self._create_from_template(p, c)):
            with ui.row().classes("w-full items-center gap-3"):
                ui.icon(icon, color="green-7").classes("text-2xl")
                with ui.column().classes("gap-0 flex-grow"):
                    ui.label(display_name).classes("text-sm font-bold text-gray-700")
                    ui.label(description).classes("text-xs text-gray-500")

    def _extract_description(self, content: str, name: str) -> str:
        """Extract a short description from the template content."""
        descriptions = {
            "basic": "Simple article with standard sections",
            "ieee": "IEEE conference paper format",
            "acm": "ACM computing paper (acmart class)",
            "arxiv": "arXiv preprint with natbib and theorem environments",
        }

        if name.lower() in descriptions:
            return descriptions[name.lower()]

        # Try to extract from documentclass
        import re

        match = re.search(r"\\documentclass.*?\{(.+?)\}", content)
        if match:
            return f"Based on {match.group(1)} class"

        return "LaTeX template"

    async def _create_from_template(self, tmpl_path: Path, content: str):
        """Show dialog to create a new project from this template."""
        template_name = tmpl_path.stem.replace("-", " ").replace("_", " ").title()

        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label(f"New Project from {template_name}").classes(
                "text-lg font-bold"
            )
            ui.separator()

            name_input = ui.input(
                "Project name", value="my-paper"
            ).classes("w-full").props("outlined dense")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Create",
                    on_click=lambda: self._do_create(
                        name_input.value.strip(), content, dialog
                    ),
                ).props("color=primary")

        dialog.open()

    async def _do_create(self, project_name: str, template_content: str, dialog):
        """Actually create the project from the template."""
        if not project_name:
            ui.notify("Enter a project name", type="warning")
            return

        create_new_project(project_name, template=template_content)

        if self._editor_ref:
            self._editor_ref.set_content(state.content)

        ui.notify(
            f"Project '{project_name}' created from template",
            type="positive",
        )
        dialog.close()
