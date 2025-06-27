"""
Register the thinking tool for the MCP server (unified tool registration).

Usage:
    from .thinking_tool import register_thinking_tool
    register_thinking_tool(mcp)

This tool provides a dynamic, step-by-step, revisable, and branchable problem-solving process.
"""
from ..services.thinking_tool_service import ThinkingToolService


def register_thinking_tool(mcp):
    """
    Register the thinking tool with the MCP server.
    
    Features:
        - Revision and branching
        - Dynamic thought count
        - Hypothesis generation/verification
        - Optional full history reporting
        - Auto-iteration with branching exploration
    """
    thinking_tool_service = ThinkingToolService()
    thinking_tool_service.register_tools(mcp)
