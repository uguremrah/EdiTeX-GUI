"""Bibliography manager panel for parsing and editing .bib files."""
import logging
from pathlib import Path

from nicegui import ui

from src.state import state

log = logging.getLogger(__name__)

# BibTeX entry types commonly used
BIB_ENTRY_TYPES = [
    "article",
    "inproceedings",
    "book",
    "incollection",
    "phdthesis",
    "mastersthesis",
    "techreport",
    "misc",
    "unpublished",
]


def _parse_bib_file(bib_path: Path) -> list[dict]:
    """Parse a .bib file into a list of entry dicts.

    Uses bibtexparser if available, otherwise falls back to a simple regex parser.
    Each entry dict has: type, key, title, author, year, and other fields.
    """
    if not bib_path.exists():
        return []

    text = bib_path.read_text(encoding="utf-8", errors="replace")

    try:
        import bibtexparser

        library = bibtexparser.parse(text)
        entries = []
        for entry in library.entries:
            entries.append({
                "type": entry.entry_type,
                "key": entry.key,
                "title": entry.fields_dict.get("title", type("", (), {"value": ""})()).value
                    if "title" in entry.fields_dict else "",
                "author": entry.fields_dict.get("author", type("", (), {"value": ""})()).value
                    if "author" in entry.fields_dict else "",
                "year": entry.fields_dict.get("year", type("", (), {"value": ""})()).value
                    if "year" in entry.fields_dict else "",
                "journal": entry.fields_dict.get("journal", type("", (), {"value": ""})()).value
                    if "journal" in entry.fields_dict else "",
                "booktitle": entry.fields_dict.get("booktitle", type("", (), {"value": ""})()).value
                    if "booktitle" in entry.fields_dict else "",
            })
        return entries
    except ImportError:
        log.info("bibtexparser not installed, using simple parser")
        return _simple_parse_bib(text)
    except Exception:
        log.exception("bibtexparser failed, falling back to simple parser")
        return _simple_parse_bib(text)


def _simple_parse_bib(text: str) -> list[dict]:
    """Fallback simple bib parser using basic string processing."""
    import re

    entries = []
    # Match @type{key, ... }
    pattern = re.compile(
        r"@(\w+)\s*\{\s*([^,\s]+)\s*,([^@]*?)(?=\n\s*@|\Z)",
        re.DOTALL,
    )

    for match in pattern.finditer(text):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        body = match.group(3)

        if entry_type in ("comment", "string", "preamble"):
            continue

        entry = {
            "type": entry_type,
            "key": key,
            "title": "",
            "author": "",
            "year": "",
            "journal": "",
            "booktitle": "",
        }

        # Extract fields
        field_pattern = re.compile(
            r"(\w+)\s*=\s*[{\"](.+?)[}\"]", re.DOTALL
        )
        for fm in field_pattern.finditer(body):
            field_name = fm.group(1).lower()
            field_value = fm.group(2).strip()
            if field_name in entry:
                entry[field_name] = field_value

        entries.append(entry)

    return entries


def _format_bib_entry(entry: dict) -> str:
    """Format a single bib entry dict back to BibTeX string."""
    lines = [f"@{entry['type']}{{{entry['key']},"]

    field_order = ["author", "title", "year", "journal", "booktitle"]
    for field in field_order:
        value = entry.get(field, "").strip()
        if value:
            lines.append(f"  {field} = {{{value}}},")

    lines.append("}")
    return "\n".join(lines)


def _save_entries_to_bib(bib_path: Path, entries: list[dict]):
    """Write all entries back to the .bib file."""
    content_parts = ["% Bibliography entries\n"]
    for entry in entries:
        content_parts.append(_format_bib_entry(entry))
        content_parts.append("")  # blank line between entries
    bib_path.write_text("\n".join(content_parts), encoding="utf-8")
    log.info("Saved %d entries to %s", len(entries), bib_path)


class BibliographyPanel:
    """Panel for managing bibliography entries."""

    def __init__(self):
        self.container = None
        self._editor_ref = None
        self._entries: list[dict] = []
        self._bib_path: Path | None = None
        self._entries_container = None

    def set_editor(self, editor):
        """Store a reference to the LatexEditor for insert_at_cursor."""
        self._editor_ref = editor

    def build(self, parent):
        """Build the bibliography panel UI inside the given container."""
        with parent:
            self.container = ui.column().classes("w-full p-2 gap-2")
            with self.container:
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Bibliography").classes("text-sm font-bold text-gray-600")
                    ui.button(
                        icon="add",
                        on_click=self._show_add_dialog,
                    ).props("flat dense round size=sm").tooltip("Add entry")

                self._entries_container = ui.column().classes("w-full gap-1").style(
                    "max-height: 450px; overflow-y: auto;"
                )

    async def refresh(self):
        """Refresh the bibliography entries from the .bib file."""
        if self._entries_container is None:
            return

        self._entries_container.clear()

        if state.project_dir is None:
            with self._entries_container:
                ui.label("No project open").classes("text-xs text-gray-400")
            return

        # Find the .bib file
        self._bib_path = self._find_bib_file()
        if self._bib_path is None:
            with self._entries_container:
                ui.label("No .bib file found").classes("text-xs text-gray-400")
            return

        self._entries = _parse_bib_file(self._bib_path)

        with self._entries_container:
            if not self._entries:
                ui.label("No entries yet").classes("text-xs text-gray-400")
                return

            for entry in self._entries:
                self._build_entry_row(entry)

    def _find_bib_file(self) -> Path | None:
        """Find the first .bib file in the project directory."""
        if state.project_dir is None:
            return None

        bib_files = list(state.project_dir.glob("*.bib"))
        if bib_files:
            return bib_files[0]

        # Create a default one
        default_bib = state.project_dir / "references.bib"
        default_bib.write_text("% Bibliography entries\n", encoding="utf-8")
        return default_bib

    def _build_entry_row(self, entry: dict):
        """Build a compact row for a single bibliography entry."""
        key = entry.get("key", "?")
        entry_type = entry.get("type", "misc")
        title = entry.get("title", "Untitled")
        year = entry.get("year", "")

        # Truncate long titles
        display_title = title if len(title) <= 60 else title[:57] + "..."

        with ui.card().classes(
            "w-full cursor-pointer hover:bg-blue-50 p-2 transition-colors"
        ).on("click", lambda k=key: self._insert_citation(k)):
            with ui.row().classes("w-full items-start gap-2"):
                ui.badge(entry_type, color="blue").props("dense")
                with ui.column().classes("gap-0 flex-grow min-w-0"):
                    ui.label(key).classes("text-xs font-mono font-bold text-blue-700")
                    ui.label(display_title).classes(
                        "text-xs text-gray-600 break-words"
                    )
                    if year:
                        ui.label(year).classes("text-[10px] text-gray-400")

    def _insert_citation(self, key: str):
        """Insert a \\cite{key} command at the cursor."""
        text = f"\\cite{{{key}}}"
        if self._editor_ref:
            self._editor_ref.insert_at_cursor(text)
            ui.notify(f"Inserted \\cite{{{key}}}", type="positive", timeout=1500)
        else:
            ui.notify("Editor not available", type="warning")

    async def _show_add_dialog(self):
        """Show a dialog to add a new bibliography entry."""
        with ui.dialog() as dialog, ui.card().classes("w-[500px]"):
            ui.label("Add Bibliography Entry").classes("text-lg font-bold")
            ui.separator()

            entry_type = ui.select(
                BIB_ENTRY_TYPES,
                value="article",
                label="Entry Type",
            ).classes("w-full").props("outlined dense")

            cite_key = ui.input(
                "Citation Key", placeholder="author2024keyword"
            ).classes("w-full").props("outlined dense")

            title_input = ui.input(
                "Title", placeholder="Paper title"
            ).classes("w-full").props("outlined dense")

            author_input = ui.input(
                "Author(s)", placeholder="Last, First and Last, First"
            ).classes("w-full").props("outlined dense")

            year_input = ui.input(
                "Year", placeholder="2024"
            ).classes("w-full").props("outlined dense")

            journal_input = ui.input(
                "Journal / Booktitle", placeholder="Journal or conference name"
            ).classes("w-full").props("outlined dense")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Add",
                    on_click=lambda: self._add_entry(
                        dialog,
                        entry_type.value,
                        cite_key.value.strip(),
                        title_input.value.strip(),
                        author_input.value.strip(),
                        year_input.value.strip(),
                        journal_input.value.strip(),
                    ),
                ).props("color=primary")

        dialog.open()

    async def _add_entry(
        self,
        dialog,
        entry_type: str,
        key: str,
        title: str,
        author: str,
        year: str,
        journal: str,
    ):
        """Add a new entry to the .bib file."""
        if not key:
            ui.notify("Citation key is required", type="warning")
            return

        # Check for duplicate key
        for existing in self._entries:
            if existing["key"] == key:
                ui.notify(f"Key '{key}' already exists", type="warning")
                return

        new_entry = {
            "type": entry_type,
            "key": key,
            "title": title,
            "author": author,
            "year": year,
            "journal": journal if entry_type in ("article",) else "",
            "booktitle": journal if entry_type in ("inproceedings", "incollection") else "",
        }

        self._entries.append(new_entry)

        if self._bib_path:
            _save_entries_to_bib(self._bib_path, self._entries)

        ui.notify(f"Added @{entry_type}{{{key}}}", type="positive")
        dialog.close()
        await self.refresh()
