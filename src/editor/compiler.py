"""LaTeX compilation using local MiKTeX pdflatex."""
import asyncio
import logging
import re
from pathlib import Path

from src.state import state
from src.utils.config import LATEX_PATH, PDFLATEX_PATH

log = logging.getLogger(__name__)


async def compile_latex(tex_path: Path, output_dir: Path | None = None) -> bool:
    """Compile a .tex file using pdflatex.

    Runs pdflatex twice for cross-references.
    Updates state.compile_errors, state.compile_warnings, state.compile_log.
    Returns True on success.
    """
    if output_dir is None:
        output_dir = tex_path.parent

    state.is_compiling = True
    state.compile_errors = []
    state.compile_warnings = []

    # Choose compiler based on export format
    if state.export_format == "dvi":
        compiler_path = LATEX_PATH
    else:
        compiler_path = PDFLATEX_PATH

    cmd = [
        str(compiler_path),
        "-interaction=nonstopmode",
        "--enable-installer",
        "-synctex=1",
        f"-output-directory={output_dir}",
        str(tex_path),
    ]

    log.info("Compile: tex_path=%s, exists=%s", tex_path, tex_path.exists())
    log.info("Compile: cmd=%s", cmd)

    # Run pdflatex twice for cross-references
    returncode = 0
    log_text = ""
    try:
        for pass_num in range(2):
            log.info("pdflatex pass %d", pass_num + 1)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tex_path.parent),
            )
            stdout, stderr = await process.communicate()
            log_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            returncode = process.returncode
            log.info("pass %d returncode=%d, stdout_len=%d, stderr_len=%d",
                     pass_num + 1, returncode, len(log_text), len(stderr_text))
            if stderr_text:
                log.warning("pdflatex stderr: %s", stderr_text[:500])
    except Exception as e:
        log.exception("compile_latex failed with exception")
        state.compile_errors = [{"message": f"Exception: {e}", "line": 0}]
        state.is_compiling = False
        return False

    state.compile_log = log_text
    state.compile_errors = parse_errors(log_text)
    state.compile_warnings = parse_warnings(log_text)

    # Determine expected output file based on export format
    if state.export_format == "dvi":
        out_ext = ".dvi"
    else:
        out_ext = ".pdf"
    output_path = output_dir / tex_path.with_suffix(out_ext).name
    log.info("Expected output at %s, exists=%s", output_path, output_path.exists())
    state.last_compile_success = output_path.exists() and returncode == 0
    state.pdf_path = output_path if output_path.exists() else None
    state.is_compiling = False

    return state.last_compile_success


def parse_errors(log: str) -> list[dict]:
    """Parse pdflatex log for errors. Returns list of {line, message, context}."""
    errors = []
    # Pattern: ! Error message followed by l.123 offending line
    pattern = re.compile(r"^! (.+?)$\s*^l\.(\d+)(.*?)$", re.MULTILINE)
    for match in pattern.finditer(log):
        errors.append(
            {
                "message": match.group(1).strip(),
                "line": int(match.group(2)),
                "context": match.group(3).strip(),
            }
        )
    return errors


def parse_warnings(log: str) -> list[dict]:
    """Parse pdflatex log for warnings."""
    warnings = []
    pattern = re.compile(
        r"(?:LaTeX|Package \w+) Warning: (.+?)(?:\n|$)", re.MULTILINE
    )
    for match in pattern.finditer(log):
        warnings.append({"message": match.group(1).strip()})
    return warnings
