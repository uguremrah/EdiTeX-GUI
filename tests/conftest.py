"""Shared test fixtures for EdiTeX-GUI test suite."""
import pytest

from src.state import EditorState


@pytest.fixture
def fresh_state():
    """Return a fresh EditorState instance with default values."""
    return EditorState()


@pytest.fixture
def sample_latex():
    """Return a sample LaTeX document string for testing."""
    return r"""\documentclass{article}
\usepackage{amsmath}
\usepackage[utf8]{inputenc}
\usepackage{graphicx,hyperref}

\title{Sample Document}
\author{Test Author}

\begin{document}

\section{Introduction}
\label{sec:intro}
This is the introduction. See Section~\ref{sec:methods} and \autoref{sec:results}.

\subsection{Background}
\label{sec:background}
Some background information with a citation~\cite{knuth1984}.

\section{Methods}
\label{sec:methods}
We use the approach from~\cite{lamport1994,knuth1984}.

\subsubsection{Details}
Equation~\eqref{eq:main} shows the result.

\section{Results}
\label{sec:results}
Results go here. See also~\pageref{sec:intro}.

\end{document}
"""
