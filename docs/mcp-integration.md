# MCP Integration Guide

This document covers the Model Context Protocol (MCP) server that ships with EdiTeX-GUI, enabling Claude Code to read, edit, and compile LaTeX documents through AI-powered tools.

## How It Works

EdiTeX-GUI uses a two-process architecture for MCP:

```
Claude Code  ──stdio──>  MCP Server (python -m src.mcp)
                              |
                              | HTTP (httpx)
                              v
                         NiceGUI App (localhost:8080/api/*)
                              |
                              v
                         Editor State + Compiler
```

1. **Claude Code** starts the MCP server as a child process using the command in `~/.mcp.json`
2. The **MCP server** communicates with Claude over **stdio** (JSON-RPC)
3. When Claude calls a tool, the server makes an **HTTP request** to the NiceGUI app's REST API
4. The app performs the action (read, write, compile) and returns the result
5. The MCP server formats the result and sends it back to Claude

## Setup

### 1. Start the editor

The NiceGUI app must be running for the MCP server to work:

```bash
cd editex-gui
uv run python -m src.app
```

### 2. Register the MCP server

Add to `~/.mcp.json`:

```json
{
  "mcpServers": {
    "editex": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "C:\\Users\\<username>\\path\\to\\editex-gui",
        "python", "-m", "src.mcp"
      ],
      "env": {}
    }
  }
}
```

Replace the path with your actual clone location.

### 3. Verify

- The green **MCP** dot in the editor's header bar confirms the API is reachable
- In Claude Code, the `editex` server should appear in the MCP server list

## Tool Reference

### get_document_content

Read the current LaTeX source from the editor.

**Parameters:** None

**Returns:** The full document text, file path, and project directory.

**Example prompt:** "Read my LaTeX document"

---

### update_document_content

Replace the entire document content in the editor.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `content` | string | The new LaTeX source code |

**Returns:** Confirmation with character count.

**Example prompt:** "Replace the document with this LaTeX code: ..."

---

### compile_document

Save and compile the document with pdflatex (or latex for DVI). Runs two passes for cross-references.

**Parameters:** None

**Returns:** Success/failure status, list of errors and warnings, and the output PDF path.

**Example prompt:** "Compile my paper and show me any errors"

---

### get_compilation_errors

Retrieve the latest compilation errors and warnings without recompiling.

**Parameters:** None

**Returns:** Lists of errors (with line numbers) and warnings, plus the last 50 lines of the compilation log.

**Example prompt:** "What errors does my document have?"

---

### get_document_structure

Parse the document for sections, labels, references, citations, and packages.

**Parameters:** None

**Returns:** Structured lists of all document elements with line numbers.

**Example prompt:** "Show me the document structure" or "What sections does my paper have?"

---

### search_replace

Find and replace text in the document. Supports both literal strings and regular expressions.

**Parameters:**
| Name | Type | Default | Description |
|---|---|---|---|
| `search` | string | *(required)* | Text or regex pattern to find |
| `replace` | string | *(required)* | Replacement text |
| `use_regex` | boolean | `false` | Whether to treat `search` as a regex |

**Returns:** Number of replacements made, or a message if no matches were found.

**Example prompt:** "Replace all \\textbf with \\emph in my document"

---

### insert_at_position

Insert text at a specific line number. The text is inserted before the specified line.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `line` | integer | Line number to insert at (1-based) |
| `text` | string | Text to insert |

**Returns:** Confirmation with the line number.

**Example prompt:** "Add a new subsection after line 45"

---

### get_project_info

Get metadata about the current project: file path, project directory, compilation status, and PDF path.

**Parameters:** None

**Returns:** Project metadata dictionary.

**Example prompt:** "What file am I editing?" or "Where is my project?"

---

### list_project_files

List all files in the project directory (recursive).

**Parameters:** None

**Returns:** List of file paths relative to the project root, with sizes.

**Example prompt:** "What files are in my project?"

---

### read_file

Read any file in the project directory. Useful for reading `.bib`, `.sty`, `.cls`, or other auxiliary files.

**Parameters:**
| Name | Type | Description |
|---|---|---|
| `path` | string | File path (relative to project or absolute within project) |

**Returns:** The file contents.

**Security:** Path traversal is blocked -- only files within the project directory can be read.

**Example prompt:** "Read my references.bib file"

## Example Workflows

### Fix compilation errors

```
You: Compile my document and fix any errors
Claude: [calls compile_document] -> sees errors
Claude: [calls get_document_content] -> reads source
Claude: [calls search_replace or update_document_content] -> fixes issues
Claude: [calls compile_document] -> verifies fix
```

### Add a bibliography entry

```
You: Add a citation for "Attention Is All You Need" by Vaswani et al. 2017
Claude: [calls read_file("references.bib")] -> reads current .bib
Claude: [calls get_document_content] -> finds where to cite
Claude: [calls update_document_content] -> adds \cite and .bib entry
Claude: [calls compile_document] -> verifies compilation
```

### Restructure a document

```
You: Move the Related Work section to after the Method section
Claude: [calls get_document_structure] -> sees section order
Claude: [calls get_document_content] -> reads full source
Claude: [calls update_document_content] -> rearranges sections
Claude: [calls compile_document] -> verifies output
```

## Developing New Tools

To add a new MCP tool:

1. **Add an API endpoint** in `src/api.py` (if the tool needs new backend functionality)
2. **Add a bridge method** in `src/mcp/bridge.py` to call the new endpoint
3. **Add a tool function** in `src/mcp/server.py` with the `@mcp.tool()` decorator
4. **Restart** both the NiceGUI app and the Claude Code session

Example:

```python
# In src/mcp/server.py
@mcp.tool()
async def word_count() -> str:
    """Count the number of words in the current document."""
    data = await bridge.get_document()
    content = data.get("content", "")
    count = len(content.split())
    return f"Document contains {count} words."
```
