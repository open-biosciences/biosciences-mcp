"""Wire-level contract tests for ADR-001 (Agentic-First Architecture).

These tests exercise every MCP server through ``fastmcp.Client`` and inspect
the JSON an agent actually receives. They exist because unit tests that call
``model_dump()`` cannot see what FastMCP serialises.
"""
