"""File operations for LaTeX projects."""
from pathlib import Path

from src.state import state
from src.utils.config import DEFAULT_PROJECT_DIR

BASIC_TEMPLATE = r"""\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{graphicx}

\title{Untitled Document}
\author{Author Name}
\date{\today}

\begin{document}

\maketitle

\section{Introduction}

Your text here.

\end{document}
"""


def create_new_project(name: str, template: str = BASIC_TEMPLATE) -> Path:
    """Create a new LaTeX project directory with standard structure."""
    project_dir = DEFAULT_PROJECT_DIR / name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "figures").mkdir(exist_ok=True)
    (project_dir / "sections").mkdir(exist_ok=True)

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        main_tex.write_text(template, encoding="utf-8")

    # Create empty bibliography
    bib_file = project_dir / "references.bib"
    if not bib_file.exists():
        bib_file.write_text("% Bibliography entries\n", encoding="utf-8")

    state.project_dir = project_dir
    state.file_path = main_tex
    state.content = main_tex.read_text(encoding="utf-8")
    return project_dir


def open_file(path: Path) -> str:
    """Open a .tex file and return its content."""
    content = path.read_text(encoding="utf-8")
    state.file_path = path
    state.project_dir = path.parent
    state.content = content
    return content


def save_file(content: str, path: Path | None = None) -> Path:
    """Save content to the current file or a specified path."""
    target = path or state.file_path
    if target is None:
        raise ValueError("No file path specified")
    target.write_text(content, encoding="utf-8")
    state.content = content
    state.file_path = target
    return target
