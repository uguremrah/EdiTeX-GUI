"""Entry point for running the MCP server: python -m src.mcp"""
from src.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
