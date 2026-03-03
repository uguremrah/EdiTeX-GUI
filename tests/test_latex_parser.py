"""Tests for src.utils.latex_parser.parse_structure."""
import pytest

from src.utils.latex_parser import parse_structure


class TestParseSections:
    """Tests for section, subsection, and subsubsection parsing."""

    def test_parse_section(self):
        content = r"\section{Introduction}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "section"
        assert result["sections"][0]["title"] == "Introduction"
        assert result["sections"][0]["line"] == 1

    def test_parse_subsection(self):
        content = r"\subsection{Background}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "subsection"
        assert result["sections"][0]["title"] == "Background"

    def test_parse_subsubsection(self):
        content = r"\subsubsection{Details}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "subsubsection"
        assert result["sections"][0]["title"] == "Details"

    def test_parse_starred_section(self):
        content = r"\section*{Acknowledgements}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "section"
        assert result["sections"][0]["title"] == "Acknowledgements"

    def test_parse_multiple_sections_preserves_order_and_line_numbers(self):
        content = (
            "\\section{First}\n"
            "Some text.\n"
            "\\subsection{Second}\n"
            "More text.\n"
            "\\subsubsection{Third}\n"
        )
        result = parse_structure(content)
        sections = result["sections"]
        assert len(sections) == 3
        assert sections[0] == {"type": "section", "title": "First", "line": 1}
        assert sections[1] == {"type": "subsection", "title": "Second", "line": 3}
        assert sections[2] == {"type": "subsubsection", "title": "Third", "line": 5}

    def test_parse_chapter(self):
        content = r"\chapter{Literature Review}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "chapter"
        assert result["sections"][0]["title"] == "Literature Review"

    def test_parse_part(self):
        content = r"\part{Foundations}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "part"

    def test_parse_paragraph(self):
        content = r"\paragraph{A detail}"
        result = parse_structure(content)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["type"] == "paragraph"
        assert result["sections"][0]["title"] == "A detail"


class TestParseLabels:
    """Tests for \\label parsing."""

    def test_single_label(self):
        content = r"\label{sec:intro}"
        result = parse_structure(content)
        assert len(result["labels"]) == 1
        assert result["labels"][0] == {"name": "sec:intro", "line": 1}

    def test_multiple_labels_on_different_lines(self):
        content = "\\label{sec:intro}\n\\label{fig:diagram}\n\\label{eq:main}"
        result = parse_structure(content)
        labels = result["labels"]
        assert len(labels) == 3
        assert labels[0]["name"] == "sec:intro"
        assert labels[1]["name"] == "fig:diagram"
        assert labels[2]["name"] == "eq:main"
        assert labels[0]["line"] == 1
        assert labels[1]["line"] == 2
        assert labels[2]["line"] == 3

    def test_label_on_same_line_as_section(self):
        content = r"\section{Intro}\label{sec:intro}"
        result = parse_structure(content)
        assert len(result["labels"]) == 1
        assert result["labels"][0]["name"] == "sec:intro"
        assert result["labels"][0]["line"] == 1


class TestParseReferences:
    """Tests for \\ref, \\eqref, \\autoref, \\pageref parsing."""

    def test_ref(self):
        content = r"See~\ref{sec:intro}"
        result = parse_structure(content)
        assert len(result["references"]) == 1
        assert result["references"][0]["name"] == "sec:intro"

    def test_eqref(self):
        content = r"Equation~\eqref{eq:main}"
        result = parse_structure(content)
        assert len(result["references"]) == 1
        assert result["references"][0]["name"] == "eq:main"

    def test_autoref(self):
        content = r"See \autoref{sec:methods}"
        result = parse_structure(content)
        assert len(result["references"]) == 1
        assert result["references"][0]["name"] == "sec:methods"

    def test_pageref(self):
        content = r"On page~\pageref{sec:intro}"
        result = parse_structure(content)
        assert len(result["references"]) == 1
        assert result["references"][0]["name"] == "sec:intro"

    def test_multiple_refs_on_same_line(self):
        content = r"See~\ref{sec:intro} and \autoref{sec:methods}"
        result = parse_structure(content)
        refs = result["references"]
        assert len(refs) == 2
        assert refs[0]["name"] == "sec:intro"
        assert refs[1]["name"] == "sec:methods"

    def test_refs_preserve_line_numbers(self):
        content = "Some text.\n\\ref{fig:a}\n\\eqref{eq:b}"
        result = parse_structure(content)
        assert result["references"][0]["line"] == 2
        assert result["references"][1]["line"] == 3


class TestParseCitations:
    """Tests for \\cite parsing with single and multiple keys."""

    def test_single_cite(self):
        content = r"\cite{knuth1984}"
        result = parse_structure(content)
        assert len(result["citations"]) == 1
        assert result["citations"][0]["key"] == "knuth1984"

    def test_multiple_keys_in_single_cite(self):
        content = r"\cite{knuth1984,lamport1994}"
        result = parse_structure(content)
        citations = result["citations"]
        assert len(citations) == 2
        assert citations[0]["key"] == "knuth1984"
        assert citations[1]["key"] == "lamport1994"

    def test_cite_with_optional_argument(self):
        content = r"\cite[p.~42]{knuth1984}"
        result = parse_structure(content)
        assert len(result["citations"]) == 1
        assert result["citations"][0]["key"] == "knuth1984"

    def test_multiple_keys_with_spaces(self):
        content = r"\cite{alpha, beta, gamma}"
        result = parse_structure(content)
        citations = result["citations"]
        assert len(citations) == 3
        assert citations[0]["key"] == "alpha"
        assert citations[1]["key"] == "beta"
        assert citations[2]["key"] == "gamma"

    def test_cite_preserves_line_number(self):
        content = "Text.\n\\cite{ref1}\nMore.\n\\cite{ref2}"
        result = parse_structure(content)
        assert result["citations"][0]["line"] == 2
        assert result["citations"][1]["line"] == 4


class TestParsePackages:
    """Tests for \\usepackage parsing."""

    def test_single_package(self):
        content = r"\usepackage{amsmath}"
        result = parse_structure(content)
        assert len(result["packages"]) == 1
        assert result["packages"][0]["name"] == "amsmath"

    def test_package_with_options(self):
        content = r"\usepackage[utf8]{inputenc}"
        result = parse_structure(content)
        assert len(result["packages"]) == 1
        assert result["packages"][0]["name"] == "inputenc"

    def test_multiple_packages_in_single_usepackage(self):
        content = r"\usepackage{graphicx,hyperref}"
        result = parse_structure(content)
        packages = result["packages"]
        assert len(packages) == 2
        assert packages[0]["name"] == "graphicx"
        assert packages[1]["name"] == "hyperref"

    def test_multiple_packages_with_spaces(self):
        content = r"\usepackage{amsmath, amssymb, amsthm}"
        result = parse_structure(content)
        packages = result["packages"]
        assert len(packages) == 3
        assert packages[0]["name"] == "amsmath"
        assert packages[1]["name"] == "amssymb"
        assert packages[2]["name"] == "amsthm"

    def test_packages_preserve_line_number(self):
        content = "\\usepackage{amsmath}\n\\usepackage{graphicx}"
        result = parse_structure(content)
        assert result["packages"][0]["line"] == 1
        assert result["packages"][1]["line"] == 2


class TestEdgeCases:
    """Tests for empty and minimal documents."""

    def test_empty_document(self):
        result = parse_structure("")
        assert result["sections"] == []
        assert result["labels"] == []
        assert result["references"] == []
        assert result["citations"] == []
        assert result["packages"] == []

    def test_document_with_no_structure_elements(self):
        content = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Hello, world!\n"
            "\\end{document}\n"
        )
        result = parse_structure(content)
        assert result["sections"] == []
        assert result["labels"] == []
        assert result["references"] == []
        assert result["citations"] == []
        assert result["packages"] == []

    def test_only_text_content(self):
        content = "This is plain text with no LaTeX commands."
        result = parse_structure(content)
        for key in ("sections", "labels", "references", "citations", "packages"):
            assert result[key] == []

    def test_result_keys_always_present(self):
        result = parse_structure("")
        assert set(result.keys()) == {
            "sections",
            "labels",
            "references",
            "citations",
            "packages",
        }


class TestFullDocument:
    """Integration-style test using the sample_latex fixture."""

    def test_full_document_parsing(self, sample_latex):
        result = parse_structure(sample_latex)

        # Sections: Introduction, Background, Methods, Details, Results
        assert len(result["sections"]) == 5
        section_types = [s["type"] for s in result["sections"]]
        assert section_types == [
            "section",
            "subsection",
            "section",
            "subsubsection",
            "section",
        ]
        section_titles = [s["title"] for s in result["sections"]]
        assert "Introduction" in section_titles
        assert "Background" in section_titles
        assert "Methods" in section_titles
        assert "Details" in section_titles
        assert "Results" in section_titles

        # Labels: sec:intro, sec:background, sec:methods, sec:results
        label_names = [l["name"] for l in result["labels"]]
        assert "sec:intro" in label_names
        assert "sec:background" in label_names
        assert "sec:methods" in label_names
        assert "sec:results" in label_names

        # References: sec:methods, sec:results, eq:main, sec:intro
        ref_names = [r["name"] for r in result["references"]]
        assert "sec:methods" in ref_names
        assert "sec:results" in ref_names
        assert "eq:main" in ref_names
        assert "sec:intro" in ref_names

        # Citations: knuth1984 (twice), lamport1994
        cite_keys = [c["key"] for c in result["citations"]]
        assert cite_keys.count("knuth1984") == 2
        assert "lamport1994" in cite_keys

        # Packages: amsmath, inputenc, graphicx, hyperref
        pkg_names = [p["name"] for p in result["packages"]]
        assert "amsmath" in pkg_names
        assert "inputenc" in pkg_names
        assert "graphicx" in pkg_names
        assert "hyperref" in pkg_names
