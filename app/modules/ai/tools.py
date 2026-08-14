"""AI tools: file and command operations the agent can perform."""
from __future__ import annotations

import json
from typing import Any

from app.modules.files.services import FileService


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the project workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path to the file."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating it if it doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "content": {"type": "string", "description": "Full file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific string in a file with a new string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "old_string": {"type": "string", "description": "Exact string to find."},
                    "new_string": {"type": "string", "description": "Replacement string."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or directory from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path to delete."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the file tree of the project.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Subdirectory path (optional)."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a text query across project files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "path": {"type": "string", "description": "Subdirectory to search (optional)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show git diff of the project.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def execute_tool(tool_name: str, arguments: dict[str, Any], file_service: FileService) -> str:
    try:
        if tool_name == "read_file":
            return file_service.read_file(arguments["path"])
        elif tool_name == "write_file":
            file_service.write_file(arguments["path"], arguments["content"])
            return f"File written: {arguments['path']}"
        elif tool_name == "edit_file":
            content = file_service.read_file(arguments["path"])
            new_content = content.replace(arguments["old_string"], arguments["new_string"])
            file_service.write_file(arguments["path"], new_content)
            return f"File edited: {arguments['path']}"
        elif tool_name == "delete_file":
            deleted = file_service.delete_file(arguments["path"])
            return f"Deleted: {arguments['path']}" if deleted else f"Not found: {arguments['path']}"
        elif tool_name == "list_files":
            tree = file_service.list_tree(arguments.get("path", ""))
            return json.dumps(tree, indent=2, default=str)
        elif tool_name == "search_files":
            results = file_service.search_files(arguments["query"], arguments.get("path", ""))
            return json.dumps(results, indent=2, default=str)
        elif tool_name == "git_diff":
            from app.modules.git.services import GitService
            git = GitService(file_service.workspace)
            result = await git.diff()
            return result.output or result.error or "No changes"
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool error: {e}"
