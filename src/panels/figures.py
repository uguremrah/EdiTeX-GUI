"""Figure gallery panel for browsing and inserting images."""
import logging
from pathlib import Path

from fastapi import Response
from nicegui import app, ui

from src.state import state

log = logging.getLogger(__name__)

# Supported image extensions
FIGURE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".eps"}


@app.get("/api/figure/{filename}")
async def serve_figure(filename: str):
    """Serve a figure file from the project's figures/ directory."""
    if state.project_dir is None:
        return Response(status_code=404)

    fig_path = state.project_dir / "figures" / filename
    if not fig_path.exists() or not fig_path.is_file():
        return Response(status_code=404)

    suffix = fig_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".eps": "application/postscript",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    data = fig_path.read_bytes()
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )


class FigurePanel:
    """Panel showing thumbnails of project figures with upload support."""

    def __init__(self):
        self.container = None
        self._editor_ref = None
        self._gallery = None

    def set_editor(self, editor):
        """Store a reference to the LatexEditor for insert_at_cursor."""
        self._editor_ref = editor

    def build(self, parent):
        """Build the figure gallery UI inside the given container."""
        with parent:
            self.container = ui.column().classes("w-full p-2 gap-2")
            with self.container:
                ui.label("Figures").classes("text-sm font-bold text-gray-600")

                # Upload button
                ui.upload(
                    label="Upload Image",
                    on_upload=self._handle_upload,
                    auto_upload=True,
                    multiple=True,
                ).classes("w-full").props(
                    'accept=".jpg,.jpeg,.png,.pdf,.eps" flat dense'
                )

                # Gallery grid placeholder
                self._gallery = ui.element("div").classes(
                    "w-full grid grid-cols-3 gap-2"
                ).style("max-height: 400px; overflow-y: auto;")

    async def refresh(self):
        """Refresh the figure gallery from the project's figures/ directory."""
        if self._gallery is None:
            return

        self._gallery.clear()

        if state.project_dir is None:
            with self._gallery:
                ui.label("No project open").classes("text-xs text-gray-400 col-span-3")
            return

        fig_dir = state.project_dir / "figures"
        if not fig_dir.exists():
            fig_dir.mkdir(parents=True, exist_ok=True)

        figures = sorted(
            [
                f
                for f in fig_dir.iterdir()
                if f.is_file() and f.suffix.lower() in FIGURE_EXTENSIONS
            ],
            key=lambda p: p.name.lower(),
        )

        with self._gallery:
            if not figures:
                ui.label("No figures yet").classes(
                    "text-xs text-gray-400 col-span-3"
                )
                return

            for fig in figures:
                self._build_thumbnail(fig)

    def _build_thumbnail(self, fig_path: Path):
        """Build a single clickable thumbnail card."""
        filename = fig_path.name
        suffix = fig_path.suffix.lower()

        with ui.card().classes(
            "cursor-pointer hover:shadow-lg transition-shadow p-1"
        ).on("click", lambda f=filename: self._insert_figure(f)):
            if suffix in {".jpg", ".jpeg", ".png"}:
                ui.image(f"/api/figure/{filename}").classes(
                    "w-full h-16 object-cover rounded"
                )
            else:
                # For PDF/EPS, show an icon placeholder
                with ui.element("div").classes(
                    "w-full h-16 flex items-center justify-center bg-gray-100 rounded"
                ):
                    ui.icon(
                        "picture_as_pdf" if suffix == ".pdf" else "image",
                        color="gray",
                    ).classes("text-2xl")

            ui.label(filename).classes(
                "text-[10px] text-gray-600 truncate w-full text-center"
            )

    def _insert_figure(self, filename: str):
        """Insert an \\includegraphics command at the cursor."""
        text = f"\\includegraphics[width=0.8\\textwidth]{{figures/{filename}}}"
        if self._editor_ref:
            self._editor_ref.insert_at_cursor(text)
            ui.notify(f"Inserted {filename}", type="positive", timeout=1500)
        else:
            ui.notify("Editor not available", type="warning")

    async def _handle_upload(self, e):
        """Handle file upload to the project's figures/ directory."""
        if state.project_dir is None:
            ui.notify("No project open. Create or open a project first.", type="warning")
            return

        fig_dir = state.project_dir / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)

        filename = e.name
        dest = fig_dir / filename

        # Write uploaded content to the figures directory
        dest.write_bytes(e.content.read())

        log.info("Uploaded figure: %s -> %s", filename, dest)
        ui.notify(f"Uploaded {filename}", type="positive", timeout=2000)

        await self.refresh()
