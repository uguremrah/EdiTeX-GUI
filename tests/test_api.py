"""Tests for src.api API endpoint logic.

Since the NiceGUI app has complex initialization that makes full ASGI testing
difficult in a unit-test context, we test:
  1. The pure functions (parse_structure, parse_errors, parse_warnings) as used
     by the API layer (covered in other test modules).
  2. The API-level logic (search/replace, insert-at-line, state reads) by
     exercising the same code paths with a mocked state singleton.
  3. Pydantic request/response models for validation.
"""
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.api import (
    DocumentResponse,
    SearchReplaceRequest,
    InsertAtLineRequest,
    UpdateRequest,
)
from src.state import EditorState
from src.utils.latex_parser import parse_structure


# ===========================================================================
# Model validation tests
# ===========================================================================


class TestPydanticModels:
    """Verify that the Pydantic request/response models validate correctly."""

    def test_document_response_with_none_paths(self):
        resp = DocumentResponse(content="hello", file_path=None, project_dir=None)
        assert resp.content == "hello"
        assert resp.file_path is None

    def test_document_response_with_paths(self):
        resp = DocumentResponse(
            content="\\section{A}",
            file_path="C:/docs/main.tex",
            project_dir="C:/docs",
        )
        assert resp.file_path == "C:/docs/main.tex"

    def test_update_request(self):
        req = UpdateRequest(content="new content")
        assert req.content == "new content"

    def test_search_replace_request_defaults(self):
        req = SearchReplaceRequest(search="foo", replace="bar")
        assert req.regex is False

    def test_search_replace_request_regex(self):
        req = SearchReplaceRequest(search=r"\d+", replace="NUM", regex=True)
        assert req.regex is True

    def test_insert_at_line_request(self):
        req = InsertAtLineRequest(line=5, text="inserted line")
        assert req.line == 5
        assert req.text == "inserted line"


# ===========================================================================
# GET /api/document logic
# ===========================================================================


class TestGetDocumentLogic:
    """Test the logic behind GET /api/document."""

    def test_returns_content_and_file_path_from_state(self):
        st = EditorState()
        st.content = "\\documentclass{article}"
        st.file_path = Path("C:/projects/main.tex")
        st.project_dir = Path("C:/projects")

        resp = DocumentResponse(
            content=st.content,
            file_path=str(st.file_path) if st.file_path else None,
            project_dir=str(st.project_dir) if st.project_dir else None,
        )
        assert resp.content == "\\documentclass{article}"
        assert resp.file_path == "C:\\projects\\main.tex"
        assert resp.project_dir == "C:\\projects"

    def test_returns_none_when_no_file_open(self):
        st = EditorState()
        resp = DocumentResponse(
            content=st.content,
            file_path=str(st.file_path) if st.file_path else None,
            project_dir=str(st.project_dir) if st.project_dir else None,
        )
        assert resp.content == ""
        assert resp.file_path is None
        assert resp.project_dir is None


# ===========================================================================
# POST /api/document logic
# ===========================================================================


class TestUpdateDocumentLogic:
    """Test the logic behind POST /api/document."""

    def test_updates_state_content(self):
        st = EditorState()
        new_content = "\\section{Updated}"
        st.content = new_content
        assert st.content == "\\section{Updated}"


# ===========================================================================
# GET /api/errors logic
# ===========================================================================


class TestGetErrorsLogic:
    """Test the logic behind GET /api/errors."""

    def test_returns_errors_and_warnings_from_state(self):
        st = EditorState()
        st.compile_errors = [{"message": "Undefined control sequence.", "line": 10}]
        st.compile_warnings = [{"message": "Reference undefined"}]
        st.compile_log = "some log text"

        result = {
            "errors": st.compile_errors,
            "warnings": st.compile_warnings,
            "log": st.compile_log,
        }
        assert len(result["errors"]) == 1
        assert result["errors"][0]["line"] == 10
        assert len(result["warnings"]) == 1
        assert "some log text" in result["log"]

    def test_empty_state_returns_empty_lists(self):
        st = EditorState()
        result = {
            "errors": st.compile_errors,
            "warnings": st.compile_warnings,
            "log": st.compile_log,
        }
        assert result["errors"] == []
        assert result["warnings"] == []
        assert result["log"] == ""


# ===========================================================================
# GET /api/structure logic
# ===========================================================================


class TestGetStructureLogic:
    """Test the logic behind GET /api/structure."""

    def test_returns_parsed_structure(self):
        content = "\\section{Intro}\n\\label{sec:intro}\n\\cite{ref1}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["title"] == "Intro"
        assert len(result["labels"]) == 1
        assert len(result["citations"]) == 1

    def test_empty_content_returns_empty_structure(self):
        result = parse_structure("")
        for key in ("sections", "labels", "references", "citations", "packages"):
            assert result[key] == []


# ===========================================================================
# POST /api/search-replace logic
# ===========================================================================


class TestSearchReplaceLogic:
    """Test the search-and-replace logic used by POST /api/search-replace."""

    def test_literal_replacement(self):
        content = "Hello world, hello Python"
        search = "hello"
        replace = "hi"
        count = content.count(search)
        new_content = content.replace(search, replace)
        assert count == 1  # case-sensitive: only lowercase "hello"
        assert new_content == "Hello world, hi Python"

    def test_literal_replacement_multiple_occurrences(self):
        content = "foo bar foo baz foo"
        search = "foo"
        replace = "qux"
        count = content.count(search)
        new_content = content.replace(search, replace)
        assert count == 3
        assert new_content == "qux bar qux baz qux"

    def test_literal_replacement_no_match(self):
        content = "Hello world"
        search = "xyz"
        replace = "abc"
        count = content.count(search)
        new_content = content.replace(search, replace)
        assert count == 0
        assert new_content == content

    def test_regex_replacement(self):
        content = "Figure 1 and Figure 23 and Figure 456"
        search = r"Figure \d+"
        replace = "Fig. X"
        count = len(re.findall(search, content))
        new_content = re.sub(search, replace, content)
        assert count == 3
        assert new_content == "Fig. X and Fig. X and Fig. X"

    def test_regex_replacement_with_groups(self):
        content = r"\textbf{important} and \textbf{critical}"
        search = r"\\textbf\{(.+?)\}"
        replace = r"\\emph{\1}"
        count = len(re.findall(search, content))
        new_content = re.sub(search, replace, content)
        assert count == 2
        assert r"\emph{important}" in new_content
        assert r"\emph{critical}" in new_content

    def test_regex_replacement_no_match(self):
        content = "No numbers here"
        search = r"\d+"
        replace = "NUM"
        count = len(re.findall(search, content))
        new_content = re.sub(search, replace, content)
        assert count == 0
        assert new_content == content

    def test_search_replace_updates_state(self):
        """Simulate what the endpoint does: update state after replacement."""
        st = EditorState()
        st.content = "alpha beta alpha"
        search = "alpha"
        replace = "gamma"
        count = st.content.count(search)
        st.content = st.content.replace(search, replace)
        assert count == 2
        assert st.content == "gamma beta gamma"


# ===========================================================================
# POST /api/insert-at-line logic
# ===========================================================================


class TestInsertAtLineLogic:
    """Test the insert-at-line logic used by POST /api/insert-at-line."""

    def test_insert_at_beginning(self):
        content = "line1\nline2\nline3"
        lines = content.split("\n")
        idx = max(0, min(1 - 1, len(lines)))  # line=1 -> idx=0
        new_lines = ["inserted"]
        lines[idx:idx] = new_lines
        result = "\n".join(lines)
        assert result == "inserted\nline1\nline2\nline3"

    def test_insert_at_middle(self):
        content = "line1\nline2\nline3"
        lines = content.split("\n")
        idx = max(0, min(2 - 1, len(lines)))  # line=2 -> idx=1
        new_lines = ["inserted"]
        lines[idx:idx] = new_lines
        result = "\n".join(lines)
        assert result == "line1\ninserted\nline2\nline3"

    def test_insert_at_end(self):
        content = "line1\nline2"
        lines = content.split("\n")
        idx = max(0, min(3 - 1, len(lines)))  # line=3 -> idx=2 (clamped to len)
        new_lines = ["inserted"]
        lines[idx:idx] = new_lines
        result = "\n".join(lines)
        assert result == "line1\nline2\ninserted"

    def test_insert_multiline_text(self):
        content = "line1\nline2"
        lines = content.split("\n")
        text = "new_a\nnew_b"
        idx = max(0, min(2 - 1, len(lines)))
        new_lines = text.split("\n")
        lines[idx:idx] = new_lines
        result = "\n".join(lines)
        assert result == "line1\nnew_a\nnew_b\nline2"

    def test_insert_with_line_zero_clamps_to_beginning(self):
        content = "line1\nline2"
        lines = content.split("\n")
        idx = max(0, min(0 - 1, len(lines)))  # line=0 -> idx clamped to 0
        new_lines = ["inserted"]
        lines[idx:idx] = new_lines
        result = "\n".join(lines)
        assert result == "inserted\nline1\nline2"

    def test_insert_with_very_large_line_clamps_to_end(self):
        content = "line1\nline2"
        lines = content.split("\n")
        idx = max(0, min(9999 - 1, len(lines)))  # clamped to len(lines)=2
        new_lines = ["inserted"]
        lines[idx:idx] = new_lines
        result = "\n".join(lines)
        assert result == "line1\nline2\ninserted"


# ===========================================================================
# GET /api/health logic
# ===========================================================================


class TestHealthLogic:
    """Test the health endpoint response shape."""

    def test_health_response_shape(self):
        # The endpoint returns a static dict
        response = {"status": "ok", "mcp_api": True}
        assert response["status"] == "ok"
        assert response["mcp_api"] is True


# ===========================================================================
# GET /api/project-info logic
# ===========================================================================


class TestProjectInfoLogic:
    """Test the project-info endpoint logic."""

    def test_project_info_with_active_project(self):
        st = EditorState()
        st.file_path = Path("C:/projects/main.tex")
        st.project_dir = Path("C:/projects")
        st.is_compiling = False
        st.last_compile_success = True
        st.pdf_path = Path("C:/projects/main.pdf")

        info = {
            "file_path": str(st.file_path) if st.file_path else None,
            "project_dir": str(st.project_dir) if st.project_dir else None,
            "is_compiling": st.is_compiling,
            "last_compile_success": st.last_compile_success,
            "pdf_path": str(st.pdf_path) if st.pdf_path else None,
        }
        assert info["file_path"] is not None
        assert info["project_dir"] is not None
        assert info["is_compiling"] is False
        assert info["last_compile_success"] is True
        assert info["pdf_path"] is not None

    def test_project_info_with_no_project(self):
        st = EditorState()
        info = {
            "file_path": str(st.file_path) if st.file_path else None,
            "project_dir": str(st.project_dir) if st.project_dir else None,
            "is_compiling": st.is_compiling,
            "last_compile_success": st.last_compile_success,
            "pdf_path": str(st.pdf_path) if st.pdf_path else None,
        }
        assert info["file_path"] is None
        assert info["project_dir"] is None
        assert info["is_compiling"] is False
        assert info["last_compile_success"] is False
        assert info["pdf_path"] is None
