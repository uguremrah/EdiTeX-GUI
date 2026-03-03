"""Tests for src.editor.compiler parse_errors and parse_warnings."""
import pytest

from src.editor.compiler import parse_errors, parse_warnings


# ---------------------------------------------------------------------------
# Realistic log fragments
# ---------------------------------------------------------------------------

PDFLATEX_ERROR_LOG = r"""This is pdfTeX, Version 3.141592653-2.6-1.40.25 (MiKTeX 24.1)
entering extended mode
(./main.tex
LaTeX2e <2023-11-01> patch level 1

! Undefined control sequence.
l.42 \badcommand
                {test}
! Missing $ inserted.
l.57 Some math x^2
                    without math mode
"""

PDFLATEX_WARNING_LOG = r"""This is pdfTeX, Version 3.141592653-2.6-1.40.25 (MiKTeX 24.1)
(./main.tex
LaTeX Warning: Reference `sec:missing' on page 1 undefined on input line 23.

LaTeX Warning: There were undefined references.

Package hyperref Warning: Token not allowed in a PDF string (Unicode):
"""

CLEAN_LOG = r"""This is pdfTeX, Version 3.141592653-2.6-1.40.25 (MiKTeX 24.1)
entering extended mode
(./main.tex
LaTeX2e <2023-11-01> patch level 1
Output written on main.pdf (3 pages, 42000 bytes).
Transcript written on main.log.
"""

MULTIPLE_ERRORS_LOG = r"""
! LaTeX Error: File `nosuchpackage.sty' not found.
l.3 \usepackage
               {nosuchpackage}
! Undefined control sequence.
l.10 \fakecmd
             some text
! Emergency stop.
l.99 \end
        {document}
"""

PACKAGE_WARNING_LOG = r"""
Package natbib Warning: Citation `smith2020' on page 2 undefined on input line 45.

Package float Warning: Floating figure forced to end of document.

LaTeX Warning: Label `tab:results' multiply defined.
"""


# ===========================================================================
# parse_errors tests
# ===========================================================================


class TestParseErrors:
    """Tests for parse_errors function."""

    def test_typical_pdflatex_errors(self):
        errors = parse_errors(PDFLATEX_ERROR_LOG)
        assert len(errors) == 2

        # First error: Undefined control sequence at line 42
        assert errors[0]["message"] == "Undefined control sequence."
        assert errors[0]["line"] == 42
        assert isinstance(errors[0]["context"], str)

        # Second error: Missing $ at line 57
        assert errors[1]["message"] == "Missing $ inserted."
        assert errors[1]["line"] == 57

    def test_no_errors_returns_empty_list(self):
        errors = parse_errors(CLEAN_LOG)
        assert errors == []

    def test_empty_log_returns_empty_list(self):
        errors = parse_errors("")
        assert errors == []

    def test_multiple_errors(self):
        errors = parse_errors(MULTIPLE_ERRORS_LOG)
        assert len(errors) == 3
        assert errors[0]["line"] == 3
        assert errors[1]["line"] == 10
        assert errors[2]["line"] == 99

    def test_error_dict_has_required_keys(self):
        errors = parse_errors(PDFLATEX_ERROR_LOG)
        for err in errors:
            assert "message" in err
            assert "line" in err
            assert "context" in err

    def test_error_line_is_integer(self):
        errors = parse_errors(PDFLATEX_ERROR_LOG)
        for err in errors:
            assert isinstance(err["line"], int)

    def test_warnings_not_detected_as_errors(self):
        errors = parse_errors(PDFLATEX_WARNING_LOG)
        assert errors == []


# ===========================================================================
# parse_warnings tests
# ===========================================================================


class TestParseWarnings:
    """Tests for parse_warnings function."""

    def test_latex_warnings(self):
        warnings = parse_warnings(PDFLATEX_WARNING_LOG)
        assert len(warnings) >= 2
        messages = [w["message"] for w in warnings]
        # Should capture the undefined reference warning
        assert any("undefined" in m.lower() for m in messages)

    def test_package_warnings(self):
        warnings = parse_warnings(PACKAGE_WARNING_LOG)
        assert len(warnings) >= 1
        messages = [w["message"] for w in warnings]
        # natbib and float are "Package X Warning" patterns
        assert any("Citation" in m for m in messages) or any(
            "smith2020" in m for m in messages
        )

    def test_no_warnings_returns_empty_list(self):
        warnings = parse_warnings(CLEAN_LOG)
        assert warnings == []

    def test_empty_log_returns_empty_list(self):
        warnings = parse_warnings("")
        assert warnings == []

    def test_warning_dict_has_message_key(self):
        warnings = parse_warnings(PDFLATEX_WARNING_LOG)
        for w in warnings:
            assert "message" in w
            assert isinstance(w["message"], str)
            assert len(w["message"]) > 0

    def test_errors_not_detected_as_warnings(self):
        warnings = parse_warnings(PDFLATEX_ERROR_LOG)
        # Error lines starting with "!" should not be parsed as warnings
        messages = [w["message"] for w in warnings]
        assert not any(m.startswith("Undefined control") for m in messages)

    def test_mixed_log_separates_warnings_from_errors(self):
        """A log with both errors and warnings should only yield warnings."""
        mixed_log = PDFLATEX_ERROR_LOG + "\n" + PDFLATEX_WARNING_LOG
        warnings = parse_warnings(mixed_log)
        # Should have the warnings from the warning section, not the errors
        messages = [w["message"] for w in warnings]
        assert any("undefined" in m.lower() for m in messages)

    def test_latex_warning_with_multiply_defined_label(self):
        warnings = parse_warnings(PACKAGE_WARNING_LOG)
        messages = [w["message"] for w in warnings]
        assert any("multiply defined" in m for m in messages)
