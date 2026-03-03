"""Parse LaTeX source for document structure information."""
import re


def parse_structure(content: str) -> dict:
    """Extract document structure from LaTeX source.

    Returns dict with sections, labels, references, citations, packages.
    """
    sections = []
    labels = []
    refs = []
    citations = []
    packages = []

    for i, line in enumerate(content.split("\n"), start=1):
        # Sections
        sec_match = re.match(
            r"\\(part|chapter|section|subsection|subsubsection|paragraph)"
            r"\*?\{(.+?)\}",
            line,
        )
        if sec_match:
            sections.append(
                {
                    "type": sec_match.group(1),
                    "title": sec_match.group(2),
                    "line": i,
                }
            )

        # Labels
        for m in re.finditer(r"\\label\{(.+?)\}", line):
            labels.append({"name": m.group(1), "line": i})

        # References
        for m in re.finditer(r"\\(?:ref|eqref|pageref|autoref)\{(.+?)\}", line):
            refs.append({"name": m.group(1), "line": i})

        # Citations
        for m in re.finditer(r"\\cite(?:\[.*?\])?\{(.+?)\}", line):
            for key in m.group(1).split(","):
                citations.append({"key": key.strip(), "line": i})

        # Packages
        pkg_match = re.match(r"\\usepackage(?:\[.*?\])?\{(.+?)\}", line)
        if pkg_match:
            for pkg in pkg_match.group(1).split(","):
                packages.append({"name": pkg.strip(), "line": i})

    return {
        "sections": sections,
        "labels": labels,
        "references": refs,
        "citations": citations,
        "packages": packages,
    }
