"""MCP Server for the EdiTeX LaTeX editor.

Exposes editor functionality as MCP tools that Claude Code can invoke
via stdio transport. Communicates with the running NiceGUI app through
HTTP bridge calls to localhost:8080.
"""

import httpx
from mcp.server.fastmcp import FastMCP

from src.mcp.bridge import EditorBridge

mcp = FastMCP("editex-gui")
bridge = EditorBridge()

CONNECTION_ERROR_MSG = (
    "Could not connect to EdiTeX app. "
    "Make sure the editor is running at http://localhost:8080 "
    "(start it with: uv run python -m src)"
)


@mcp.tool()
async def get_document_content() -> str:
    """Read the current document content from the EdiTeX editor.

    Returns the full LaTeX source code currently loaded in the editor,
    along with the file path.
    """
    try:
        data = await bridge.get_document()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    content = data.get("content", "")
    file_path = data.get("file_path", "unknown")
    line_count = content.count("\n") + 1 if content else 0

    return (
        f"File: {file_path}\n"
        f"Lines: {line_count}\n"
        f"---\n"
        f"{content}"
    )


@mcp.tool()
async def update_document_content(content: str) -> str:
    """Replace the entire document content in the EdiTeX editor.

    Args:
        content: The new full LaTeX source to set in the editor.

    Returns a confirmation message with the file path.
    """
    try:
        data = await bridge.update_document(content)
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    file_path = data.get("file_path", "unknown")
    line_count = content.count("\n") + 1
    return (
        f"Document updated successfully.\n"
        f"File: {file_path}\n"
        f"Lines: {line_count}"
    )


@mcp.tool()
async def compile_document() -> str:
    """Save and compile the current LaTeX document with pdflatex.

    Triggers a full compilation of the document. Returns the compilation
    status including any errors and warnings.
    """
    try:
        data = await bridge.compile_document()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    success = data.get("success", False)
    errors = data.get("errors", [])
    warnings = data.get("warnings", [])

    lines = []
    lines.append(f"Compilation: {'SUCCESS' if success else 'FAILED'}")
    lines.append("")

    if errors:
        lines.append(f"Errors ({len(errors)}):")
        for err in errors:
            msg = err.get("message", str(err))
            line_num = err.get("line", "")
            prefix = f"  Line {line_num}: " if line_num else "  "
            lines.append(f"{prefix}{msg}")
        lines.append("")

    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        for warn in warnings:
            msg = warn.get("message", str(warn))
            line_num = warn.get("line", "")
            prefix = f"  Line {line_num}: " if line_num else "  "
            lines.append(f"{prefix}{msg}")
        lines.append("")

    if not errors and not warnings:
        lines.append("No errors or warnings.")

    return "\n".join(lines)


@mcp.tool()
async def get_compilation_errors() -> str:
    """Get the latest compilation errors and warnings from the EdiTeX editor.

    Returns a formatted list of errors and warnings from the most recent
    compilation attempt.
    """
    try:
        data = await bridge.get_errors()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    errors = data.get("errors", [])
    warnings = data.get("warnings", [])
    log = data.get("log", "")

    lines = []

    if errors:
        lines.append(f"Errors ({len(errors)}):")
        for err in errors:
            msg = err.get("message", str(err))
            line_num = err.get("line", "")
            prefix = f"  Line {line_num}: " if line_num else "  "
            lines.append(f"{prefix}{msg}")
        lines.append("")

    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        for warn in warnings:
            msg = warn.get("message", str(warn))
            line_num = warn.get("line", "")
            prefix = f"  Line {line_num}: " if line_num else "  "
            lines.append(f"{prefix}{msg}")
        lines.append("")

    if not errors and not warnings:
        lines.append("No errors or warnings.")

    if log:
        # Include last 30 lines of the log for context
        log_lines = log.strip().split("\n")
        tail = log_lines[-30:] if len(log_lines) > 30 else log_lines
        lines.append("--- Compilation log (last lines) ---")
        lines.extend(tail)

    return "\n".join(lines)


@mcp.tool()
async def get_document_structure() -> str:
    """Parse the current LaTeX document and return its structure.

    Returns the document's sections hierarchy, labels, cross-references,
    citations, and loaded packages.
    """
    try:
        data = await bridge.get_structure()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    lines = []

    sections = data.get("sections", [])
    if sections:
        lines.append("Sections:")
        indent_map = {
            "part": 0,
            "chapter": 1,
            "section": 2,
            "subsection": 3,
            "subsubsection": 4,
            "paragraph": 5,
        }
        for sec in sections:
            indent = "  " * indent_map.get(sec["type"], 2)
            lines.append(
                f"{indent}[{sec['type']}] {sec['title']} (line {sec['line']})"
            )
        lines.append("")

    labels = data.get("labels", [])
    if labels:
        lines.append("Labels:")
        for lbl in labels:
            lines.append(f"  {lbl['name']} (line {lbl['line']})")
        lines.append("")

    refs = data.get("references", [])
    if refs:
        lines.append("References:")
        for ref in refs:
            lines.append(f"  {ref['name']} (line {ref['line']})")
        lines.append("")

    citations = data.get("citations", [])
    if citations:
        lines.append("Citations:")
        for cit in citations:
            lines.append(f"  {cit['key']} (line {cit['line']})")
        lines.append("")

    packages = data.get("packages", [])
    if packages:
        lines.append("Packages:")
        for pkg in packages:
            lines.append(f"  {pkg['name']} (line {pkg['line']})")
        lines.append("")

    if not lines:
        lines.append("Document structure is empty (no sections, labels, or packages found).")

    return "\n".join(lines)


@mcp.tool()
async def search_replace(
    search: str, replace: str, use_regex: bool = False
) -> str:
    """Find and replace text in the current LaTeX document.

    Args:
        search: The text or regex pattern to search for.
        replace: The replacement text.
        use_regex: If True, treat search as a regular expression.

    Returns the number of replacements made.
    """
    try:
        data = await bridge.search_replace(search, replace, regex=use_regex)
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    count = data.get("replacements", 0)
    mode = "regex" if use_regex else "literal"

    if count == 0:
        return f"No matches found for '{search}' ({mode} search)."

    return (
        f"Replaced {count} occurrence(s).\n"
        f"Search ({mode}): {search}\n"
        f"Replace: {replace}"
    )


@mcp.tool()
async def insert_at_position(line: int, text: str) -> str:
    """Insert text at a specific line number in the document.

    Args:
        line: The 1-based line number where text will be inserted.
              The new text appears before the existing content at that line.
        text: The text to insert (can be multiple lines).

    Returns confirmation of the insertion.
    """
    try:
        data = await bridge.insert_at_line(line, text)
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    new_line_count = data.get("total_lines", 0)
    inserted_lines = text.count("\n") + 1
    return (
        f"Inserted {inserted_lines} line(s) at line {line}.\n"
        f"Document now has {new_line_count} lines."
    )


@mcp.tool()
async def get_project_info() -> str:
    """Get information about the current EdiTeX project.

    Returns the file path, project directory, compilation status,
    and PDF output path.
    """
    try:
        data = await bridge.get_project_info()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    lines = [
        "Project Info:",
        f"  File: {data.get('file_path', 'None')}",
        f"  Project dir: {data.get('project_dir', 'None')}",
        f"  Compiling: {data.get('is_compiling', False)}",
        f"  Last compile success: {data.get('last_compile_success', False)}",
        f"  PDF path: {data.get('pdf_path', 'None')}",
    ]
    return "\n".join(lines)


@mcp.tool()
async def list_project_files() -> str:
    """List all files in the current EdiTeX project directory.

    Returns a list of relative file paths in the project, useful for
    discovering .tex, .bib, .sty, and other supporting files.
    """
    try:
        data = await bridge.get_project_files()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    files = data.get("files", [])

    if not files:
        return "No files found in the project directory."

    lines = [f"Project files ({len(files)}):"]
    for f in sorted(files):
        lines.append(f"  {f}")
    return "\n".join(lines)


@mcp.tool()
async def read_file(path: str) -> str:
    """Read any file in the project directory.

    Useful for reading .bib bibliography files, .sty style files,
    included .tex files, or any other project file.

    Args:
        path: Relative path from the project directory (e.g. 'references.bib',
              'sections/intro.tex').

    Returns the file content.
    """
    try:
        data = await bridge.read_file(path)
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        return f"{CONNECTION_ERROR_MSG}\nDetails: {exc}"

    file_path = data.get("path", path)
    content = data.get("content", "")
    line_count = content.count("\n") + 1 if content else 0

    return (
        f"File: {file_path}\n"
        f"Lines: {line_count}\n"
        f"---\n"
        f"{content}"
    )
