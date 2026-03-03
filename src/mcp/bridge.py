"""HTTP client bridge to communicate with the EdiTeX NiceGUI app."""

import httpx

API_BASE = "http://localhost:8080/api"


class EditorBridge:
    """Async httpx client calling EdiTeX API endpoints."""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url

    async def get_document(self) -> dict:
        """Fetch the current document content, file path, and project dir."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/document")
            r.raise_for_status()
            return r.json()

    async def update_document(self, content: str) -> dict:
        """Replace the entire document content."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/document", json={"content": content}
            )
            r.raise_for_status()
            return r.json()

    async def compile_document(self) -> dict:
        """Save and compile the current document with pdflatex."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{self.base_url}/compile")
            r.raise_for_status()
            return r.json()

    async def get_errors(self) -> dict:
        """Get the latest compilation errors and warnings."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/errors")
            r.raise_for_status()
            return r.json()

    async def get_structure(self) -> dict:
        """Parse the document and return its structure."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/structure")
            r.raise_for_status()
            return r.json()

    async def search_replace(
        self, search: str, replace: str, regex: bool = False
    ) -> dict:
        """Find and replace text in the document."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/search-replace",
                json={"search": search, "replace": replace, "regex": regex},
            )
            r.raise_for_status()
            return r.json()

    async def insert_at_line(self, line: int, text: str) -> dict:
        """Insert text at a specific line number."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/insert-at-line",
                json={"line": line, "text": text},
            )
            r.raise_for_status()
            return r.json()

    async def get_project_info(self) -> dict:
        """Get information about the current project."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/project-info")
            r.raise_for_status()
            return r.json()

    async def get_project_files(self) -> dict:
        """List all files in the current project directory."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/project-files")
            r.raise_for_status()
            return r.json()

    async def read_file(self, path: str) -> dict:
        """Read a file from the project directory."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/read-file", params={"path": path}
            )
            r.raise_for_status()
            return r.json()
