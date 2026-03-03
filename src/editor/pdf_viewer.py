"""PDF preview component using PyMuPDF rendering."""
import logging
import time

import pymupdf
from fastapi import Response
from nicegui import app, ui

from src.state import state
from src.utils.config import PDF_RENDER_DPI_SCALE

log = logging.getLogger(__name__)

# In-memory store for the latest rendered page PNG
_render_store: dict = {"png_bytes": b""}


@app.get("/api/pdf-page")
async def _serve_pdf_page():
    """Serve the current PDF page as PNG."""
    data = _render_store["png_bytes"]
    if not data:
        return Response(status_code=204)
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


class PdfViewer:
    """PDF viewer that renders pages to PNG via PyMuPDF."""

    def __init__(self):
        self.page_label: ui.label | None = None
        self.pdf_name_label: ui.label | None = None
        self.zoom_label: ui.label | None = None
        self._container_id: str | None = None
        self._zoom: int = 100  # percentage

    def build(self, container):
        """Build the PDF viewer UI inside the given container."""
        with container:
            # Top bar: PDF filename
            self.pdf_name_label = ui.label("No PDF loaded").classes(
                "w-full text-center text-xs text-gray-500 font-mono py-1"
            ).style("background: #eef2f7; border-bottom: 1px solid #ddd;")

            # Navigation + zoom row
            with ui.row().classes(
                "w-full justify-center items-center gap-1 py-1"
            ).style("background: #f8fafc;"):
                ui.button(icon="first_page", on_click=self.first_page).props(
                    "flat dense round size=sm"
                )
                ui.button(icon="chevron_left", on_click=self.prev_page).props(
                    "flat dense round size=sm"
                )
                self.page_label = ui.label("0 / 0").classes(
                    "mx-1 text-sm text-gray-600"
                )
                ui.button(icon="chevron_right", on_click=self.next_page).props(
                    "flat dense round size=sm"
                )
                ui.button(icon="last_page", on_click=self.last_page).props(
                    "flat dense round size=sm"
                )

                ui.separator().props("vertical inset").classes("mx-1 opacity-30")

                ui.button(icon="remove", on_click=self.zoom_out).props(
                    "flat dense round size=sm"
                ).tooltip("Zoom out")
                self.zoom_label = ui.label("100%").classes(
                    "text-xs text-gray-500 mx-1"
                ).style("min-width: 36px; text-align: center;")
                ui.button(icon="add", on_click=self.zoom_in).props(
                    "flat dense round size=sm"
                ).tooltip("Zoom in")
                ui.button(icon="fit_screen", on_click=self.zoom_fit).props(
                    "flat dense round size=sm"
                ).tooltip("Fit to width")

            # Scrollable image container
            el = ui.element("div").classes("w-full").style(
                "overflow: auto; flex: 1;"
            )
            self._container_id = el.id

    async def refresh(self):
        """Re-render the current page from the PDF."""
        try:
            if state.pdf_path is None or not state.pdf_path.exists():
                if self.page_label:
                    self.page_label.text = "0 / 0"
                if self.pdf_name_label:
                    self.pdf_name_label.text = "No PDF loaded"
                return

            doc = pymupdf.open(str(state.pdf_path))
            state.total_pages = len(doc)

            if state.current_page >= state.total_pages:
                state.current_page = max(0, state.total_pages - 1)

            page = doc[state.current_page]
            mat = pymupdf.Matrix(PDF_RENDER_DPI_SCALE, PDF_RENDER_DPI_SCALE)
            pix = page.get_pixmap(matrix=mat)
            _render_store["png_bytes"] = pix.tobytes("png")
            doc.close()

            ts = int(time.time() * 1000)
            log.info(
                "Rendered page %d (%d bytes), total_pages=%d",
                state.current_page, len(_render_store["png_bytes"]), state.total_pages,
            )

            zoom = self._zoom
            js = (
                f'var c = getHtmlElement({self._container_id});'
                f'c.innerHTML = \'<img src="/api/pdf-page?t={ts}" '
                f'style="width:{zoom}%;display:block;margin:0 auto;'
                f'border:1px solid #ddd;border-radius:4px;" />\';'
            )
            ui.run_javascript(js)

            if self.pdf_name_label:
                self.pdf_name_label.text = state.pdf_path.name
            if self.page_label:
                self.page_label.text = (
                    f"{state.current_page + 1} / {state.total_pages}"
                )
        except Exception:
            log.exception("pdf_viewer.refresh failed")

    async def zoom_in(self):
        self._zoom = min(300, self._zoom + 25)
        self._update_zoom_label()
        await self.refresh()

    async def zoom_out(self):
        self._zoom = max(25, self._zoom - 25)
        self._update_zoom_label()
        await self.refresh()

    async def zoom_fit(self):
        self._zoom = 100
        self._update_zoom_label()
        await self.refresh()

    def _update_zoom_label(self):
        if self.zoom_label:
            self.zoom_label.text = f"{self._zoom}%"

    async def prev_page(self):
        if state.current_page > 0:
            state.current_page -= 1
            await self.refresh()

    async def next_page(self):
        if state.current_page < state.total_pages - 1:
            state.current_page += 1
            await self.refresh()

    async def first_page(self):
        state.current_page = 0
        await self.refresh()

    async def last_page(self):
        if state.total_pages > 0:
            state.current_page = state.total_pages - 1
            await self.refresh()
