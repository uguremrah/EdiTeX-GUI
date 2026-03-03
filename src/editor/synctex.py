"""SyncTeX integration for forward and inverse search."""
import asyncio
import logging
import re
from pathlib import Path

from src.utils.config import SYNCTEX_PATH

log = logging.getLogger(__name__)


async def forward_search(tex_path: Path, line: int) -> dict | None:
    """Run SyncTeX forward search: source line -> PDF page/coordinates.

    Args:
        tex_path: Path to the .tex source file.
        line: 1-based line number in the source.

    Returns:
        Dict with 'page', 'x', 'y' on success, or None on failure.
    """
    pdf_path = tex_path.with_suffix(".pdf")
    if not pdf_path.exists():
        log.warning("forward_search: PDF not found at %s", pdf_path)
        return None

    cmd = [
        str(SYNCTEX_PATH),
        "view",
        "-i",
        f"{line}:0:{tex_path}",
        "-o",
        str(pdf_path),
    ]

    log.info("SyncTeX forward search: %s", cmd)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(tex_path.parent),
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")
        log.debug("SyncTeX forward output: %s", output)

        if process.returncode != 0:
            log.warning(
                "SyncTeX forward search failed (rc=%d): %s",
                process.returncode,
                stderr.decode("utf-8", errors="replace"),
            )
            return None

        return _parse_forward_output(output)

    except FileNotFoundError:
        log.error("SyncTeX binary not found at %s", SYNCTEX_PATH)
        return None
    except Exception:
        log.exception("SyncTeX forward search error")
        return None


async def inverse_search(pdf_path: Path, page: int, x: float, y: float) -> dict | None:
    """Run SyncTeX inverse search: PDF position -> source line.

    Args:
        pdf_path: Path to the PDF file.
        page: 1-based page number.
        x: Horizontal coordinate in the PDF.
        y: Vertical coordinate in the PDF.

    Returns:
        Dict with 'file', 'line', 'column' on success, or None on failure.
    """
    cmd = [
        str(SYNCTEX_PATH),
        "edit",
        "-o",
        f"{page}:{x}:{y}:{pdf_path}",
    ]

    log.info("SyncTeX inverse search: %s", cmd)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(pdf_path.parent),
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")
        log.debug("SyncTeX inverse output: %s", output)

        if process.returncode != 0:
            log.warning(
                "SyncTeX inverse search failed (rc=%d): %s",
                process.returncode,
                stderr.decode("utf-8", errors="replace"),
            )
            return None

        return _parse_inverse_output(output)

    except FileNotFoundError:
        log.error("SyncTeX binary not found at %s", SYNCTEX_PATH)
        return None
    except Exception:
        log.exception("SyncTeX inverse search error")
        return None


def _parse_forward_output(output: str) -> dict | None:
    """Parse SyncTeX view output to extract page number and coordinates.

    Typical output format:
        SyncTeX result begin
        Output:...
        Page:1
        x:72.0
        y:100.0
        h:72.0
        v:100.0
        W:...
        H:...
        before:...
        offset:...
        middle:...
        after:...
        SyncTeX result end
    """
    page_match = re.search(r"^Page:(\d+)", output, re.MULTILINE)
    x_match = re.search(r"^x:([\d.]+)", output, re.MULTILINE)
    y_match = re.search(r"^y:([\d.]+)", output, re.MULTILINE)

    if page_match:
        result = {
            "page": int(page_match.group(1)),
            "x": float(x_match.group(1)) if x_match else 0.0,
            "y": float(y_match.group(1)) if y_match else 0.0,
        }
        log.info("SyncTeX forward result: %s", result)
        return result

    log.warning("Could not parse SyncTeX forward output")
    return None


def _parse_inverse_output(output: str) -> dict | None:
    """Parse SyncTeX edit output to extract source file and line.

    Typical output format:
        SyncTeX result begin
        Output:...
        Input:main.tex
        Line:42
        Column:0
        Offset:0
        Context:...
        SyncTeX result end
    """
    input_match = re.search(r"^Input:(.+)$", output, re.MULTILINE)
    line_match = re.search(r"^Line:(\d+)", output, re.MULTILINE)
    column_match = re.search(r"^Column:(-?\d+)", output, re.MULTILINE)

    if line_match:
        result = {
            "file": input_match.group(1).strip() if input_match else "",
            "line": int(line_match.group(1)),
            "column": int(column_match.group(1)) if column_match else 0,
        }
        log.info("SyncTeX inverse result: %s", result)
        return result

    log.warning("Could not parse SyncTeX inverse output")
    return None
