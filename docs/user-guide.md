# EdiTeX-GUI User Guide

A practical guide to using EdiTeX-GUI for LaTeX editing.

## Getting Started

Launch the application:

```bash
uv run python -m src.app
```

Your browser opens to `http://localhost:8080`. You'll see the editor with an empty workspace.

## Creating a New Project

1. Click **New** in the header toolbar
2. Enter a project name (e.g., "my-paper")
3. Click **Create**

This creates a project directory at `~/latex-projects/my-paper/` with:

```
my-paper/
├── main.tex          # LaTeX source (pre-filled with a basic template)
├── references.bib    # Empty bibliography file
├── figures/          # Directory for images
└── sections/         # Directory for additional .tex files
```

## Creating from a Template

1. Click the **Templates** tab in the header bar
2. Browse the available templates:
   - **Basic** -- Simple article with standard sections
   - **IEEE** -- IEEE conference paper format
   - **ACM** -- ACM computing paper (acmart class)
   - **arXiv** -- arXiv preprint with theorem environments
3. Click a template card
4. Enter a project name and click **Create**

## Opening an Existing File

1. Click **Open** in the toolbar
2. **Recent Files** appear at the top (if any) -- click one to open instantly
3. Or use the **Browse** section to navigate your filesystem:
   - Use the navigation buttons: Up, Home, Desktop, LaTeX Projects
   - Click folders to enter them
   - Click `.tex` files (green) to open them
4. Or paste a full file path in the input box at the bottom

## Editing

The editor uses **CodeMirror** with LaTeX syntax highlighting.

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+S` | Save the current document |
| `Ctrl+B` | Compile the document |

### Auto-Save

Documents are automatically saved every 30 seconds if changes have been made.

## Compiling

1. Click **Compile** (green button) or press `Ctrl+B`
2. The document is saved and compiled with pdflatex (two passes for cross-references)
3. The PDF preview appears in the right panel
4. Errors and warnings appear in the **Compilation Output** panel at the bottom

### Output Format

Toggle between **PDF** and **DVI** output using the format buttons next to Compile.

### Auto Package Installation

If MiKTeX is configured for on-the-fly installation (the default), missing LaTeX packages are downloaded automatically during compilation.

## PDF Preview

The right panel shows the compiled PDF:

- **Page navigation**: Use the arrow buttons or the page counter
- **Zoom**: Click the + / - buttons or the fit-to-width button
- The PDF filename is shown at the top of the viewer

## SyncTeX (Source-PDF Sync)

Click **SyncTeX** in the toolbar to jump from your current cursor position in the editor to the corresponding location in the PDF.

## Managing Figures

Switch to the **Figures** tab:

1. **Upload images** by clicking the upload button and selecting files (JPG, PNG, PDF, EPS)
2. Uploaded images appear as thumbnails in a grid
3. **Click a thumbnail** to insert `\includegraphics{figures/filename}` at the cursor position

## Managing Bibliography

Switch to the **Bib** tab:

1. The panel shows all entries from your project's `.bib` file
2. **Click an entry** to insert `\cite{key}` at the cursor
3. Click the **+** button to add a new entry:
   - Select entry type (article, inproceedings, book, etc.)
   - Fill in citation key, title, author, year, and journal/booktitle
   - Click **Add**

## Theme

Click the **moon/sun icon** in the toolbar to toggle between dark and light themes. This changes both the CodeMirror editor theme (VS Code Dark / GitHub Light) and the overall UI.

## MCP Status

The **MCP** indicator in the header shows the API health:
- **Green dot** -- the REST API is reachable (MCP tools will work)
- **Red dot** -- the API is unreachable

## Project File Structure

When you create a project, EdiTeX-GUI sets up:

```
~/latex-projects/
└── my-paper/
    ├── main.tex           # Your LaTeX source
    ├── main.pdf           # Compiled output (after first compile)
    ├── main.synctex.gz    # SyncTeX data (for source-PDF sync)
    ├── references.bib     # Bibliography entries
    ├── figures/            # Images for \includegraphics
    └── sections/           # Optional additional .tex files
```

## Tips

- **Compile often** to catch errors early. pdflatex is fast for most documents.
- **Use templates** for conference submissions -- they include the correct document class and formatting.
- **Click errors** in the Compilation Output panel to jump directly to the problematic line.
- **Recent files** make it fast to switch between projects -- just click Open and pick from the list.
- **Add custom templates** by dropping `.tex` files into the `templates/` directory in the EdiTeX-GUI installation folder.
