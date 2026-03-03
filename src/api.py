"""Internal FastAPI API endpoints for MCP server communication."""
import os
import re
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.editor.compiler import compile_latex
from src.editor.file_manager import save_file
from src.state import state
from src.utils.latex_parser import parse_structure

api_router = APIRouter(prefix="/api", tags=["internal"])


class DocumentResponse(BaseModel):
    content: str
    file_path: str | None
    project_dir: str | None


class UpdateRequest(BaseModel):
    content: str


class CompileResponse(BaseModel):
    success: bool
    errors: list[dict]
    warnings: list[dict]


class SearchReplaceRequest(BaseModel):
    search: str
    replace: str
    regex: bool = False


class InsertAtLineRequest(BaseModel):
    line: int
    text: str


@api_router.get("/health")
async def health():
    """Health check endpoint used by the MCP connectivity indicator."""
    return {"status": "ok", "mcp_api": True}


@api_router.get("/document", response_model=DocumentResponse)
async def get_document():
    return DocumentResponse(
        content=state.content,
        file_path=str(state.file_path) if state.file_path else None,
        project_dir=str(state.project_dir) if state.project_dir else None,
    )


@api_router.post("/document", response_model=DocumentResponse)
async def update_document(req: UpdateRequest):
    state.content = req.content
    if state.editor_element is not None:
        state.editor_element.value = req.content
    if state.file_path:
        save_file(req.content)
    return await get_document()


@api_router.post("/compile", response_model=CompileResponse)
async def compile_document():
    if state.file_path is None:
        return CompileResponse(
            success=False, errors=[{"message": "No file open"}], warnings=[]
        )
    save_file(state.content)
    success = await compile_latex(state.file_path)
    return CompileResponse(
        success=success,
        errors=state.compile_errors,
        warnings=state.compile_warnings,
    )


@api_router.get("/errors")
async def get_errors():
    return {
        "errors": state.compile_errors,
        "warnings": state.compile_warnings,
        "log": state.compile_log,
    }


@api_router.get("/structure")
async def get_structure():
    return parse_structure(state.content)


@api_router.post("/search-replace")
async def search_replace(req: SearchReplaceRequest):
    content = state.content
    if req.regex:
        count = len(re.findall(req.search, content))
        new_content = re.sub(req.search, req.replace, content)
    else:
        count = content.count(req.search)
        new_content = content.replace(req.search, req.replace)
    state.content = new_content
    if state.editor_element is not None:
        state.editor_element.value = new_content
    if state.file_path:
        save_file(new_content)
    return {"replacements": count, "content": new_content}


@api_router.post("/insert-at-line")
async def insert_at_line(req: InsertAtLineRequest):
    """Insert text at a specific 1-based line number in the document."""
    lines = state.content.split("\n")
    # Clamp line number to valid range (1-based)
    idx = max(0, min(req.line - 1, len(lines)))
    new_lines = req.text.split("\n")
    lines[idx:idx] = new_lines
    new_content = "\n".join(lines)

    state.content = new_content
    if state.editor_element is not None:
        state.editor_element.value = new_content
    if state.file_path:
        save_file(new_content)

    return {"total_lines": len(lines), "content": new_content}


@api_router.get("/project-info")
async def get_project_info():
    """Return information about the current project."""
    return {
        "file_path": str(state.file_path) if state.file_path else None,
        "project_dir": str(state.project_dir) if state.project_dir else None,
        "is_compiling": state.is_compiling,
        "last_compile_success": state.last_compile_success,
        "pdf_path": str(state.pdf_path) if state.pdf_path else None,
    }


@api_router.get("/project-files")
async def get_project_files():
    """List all files in the current project directory."""
    if state.project_dir is None:
        return {"files": []}

    project = Path(state.project_dir)
    if not project.is_dir():
        return {"files": []}

    files: list[str] = []
    for root, _dirs, filenames in os.walk(project):
        # Skip hidden directories and common build output dirs
        root_path = Path(root)
        parts = root_path.relative_to(project).parts
        if any(p.startswith(".") for p in parts):
            continue
        for fname in filenames:
            if fname.startswith("."):
                continue
            rel = (root_path / fname).relative_to(project)
            files.append(str(rel).replace("\\", "/"))

    return {"files": sorted(files)}


@api_router.get("/read-file")
async def read_file(path: str = Query(..., description="Relative path from project directory")):
    """Read a file from the project directory."""
    if state.project_dir is None:
        return {"error": "No project directory set", "content": "", "path": path}

    project = Path(state.project_dir)
    target = (project / path).resolve()

    # Security: ensure the resolved path is within the project directory
    if not str(target).startswith(str(project.resolve())):
        return {"error": "Path is outside the project directory", "content": "", "path": path}

    if not target.is_file():
        return {"error": f"File not found: {path}", "content": "", "path": path}

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": "File is not a text file", "content": "", "path": path}

    return {"content": content, "path": str(target)}
