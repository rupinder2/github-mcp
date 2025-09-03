"""
GitHub MCP Server - Core server functionality
Converted from github-mcp-server/pkg/github/server.go
"""

import json
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
from mcp.types import CallToolRequest, CallToolResult
from mcp.server.fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PaginationParams:
    """Parameters for pagination in REST API calls."""
    def __init__(self, page: int = 1, per_page: int = 30, after: str = ""):
        self.page = page
        self.per_page = per_page
        self.after = after


class CursorPaginationParams:
    """Parameters for cursor-based pagination."""
    def __init__(self, per_page: int = 30, after: str = ""):
        self.per_page = per_page
        self.after = after


class GraphQLPaginationParams:
    """Parameters for GraphQL pagination."""
    def __init__(self, first: Optional[int] = None, after: Optional[str] = None):
        self.first = first
        self.after = after


def optional_param_ok(request: CallToolRequest, param_name: str) -> Tuple[Any, bool, Optional[Exception]]:
    """
    Helper function to fetch an optional parameter from the request.
    Returns the value, whether it was present, and any error.
    """
    args = request.arguments
    if param_name not in args:
        return None, False, None

    value = args[param_name]
    return value, True, None


def required_param(request: CallToolRequest, param_name: str, param_type: Type[T]) -> Tuple[T, Optional[Exception]]:
    """
    Helper function to fetch a required parameter from the request.
    Validates that the parameter exists and is of the correct type.
    """
    args = request.arguments

    if param_name not in args:
        return None, ValueError(f"missing required parameter: {param_name}")

    value = args[param_name]
    if not isinstance(value, param_type):
        return None, ValueError(f"parameter {param_name} is not of type {param_type.__name__}, got {type(value).__name__}")

    # Check for empty values (comparable types)
    if hasattr(value, '__eq__') and value == type(value)():
        return None, ValueError(f"missing required parameter: {param_name}")

    return value, None


def required_int_param(request: CallToolRequest, param_name: str) -> Tuple[int, Optional[Exception]]:
    """
    Helper function to fetch a required integer parameter.
    Converts float values to int as needed.
    """
    value, err = required_param(request, param_name, (int, float))
    if err:
        return 0, err

    if isinstance(value, float):
        return int(value), None
    return value, None


def optional_param(request: CallToolRequest, param_name: str, param_type: Type[T]) -> Tuple[Optional[T], Optional[Exception]]:
    """
    Helper function to fetch an optional parameter from the request.
    Returns the parameter value or None if not present.
    """
    args = request.arguments

    if param_name not in args:
        return None, None

    value = args[param_name]
    if not isinstance(value, param_type):
        return None, ValueError(f"parameter {param_name} is not of type {param_type.__name__}, got {type(value).__name__}")

    return value, None


def optional_int_param(request: CallToolRequest, param_name: str) -> Tuple[Optional[int], Optional[Exception]]:
    """
    Helper function to fetch an optional integer parameter.
    Converts float values to int as needed.
    """
    value, err = optional_param(request, param_name, (int, float))
    if err:
        return None, err

    if value is None:
        return None, None

    if isinstance(value, float):
        return int(value), None
    return value, None


def optional_int_param_with_default(request: CallToolRequest, param_name: str, default: int) -> Tuple[int, Optional[Exception]]:
    """
    Helper function to fetch an optional integer parameter with a default value.
    """
    value, err = optional_int_param(request, param_name)
    if err:
        return 0, err

    if value is None:
        return default, None

    return value, None


def optional_bool_param_with_default(request: CallToolRequest, param_name: str, default: bool) -> Tuple[bool, Optional[Exception]]:
    """
    Helper function to fetch an optional boolean parameter with a default value.
    """
    args = request.arguments
    _, exists = args.get(param_name), param_name in args

    value, err = optional_param(request, param_name, bool)
    if err:
        return False, err

    if not exists:
        return default, None

    return value, None


def optional_string_array_param(request: CallToolRequest, param_name: str) -> Tuple[Optional[list], Optional[Exception]]:
    """
    Helper function to fetch an optional string array parameter.
    Handles both []string and []any types.
    """
    args = request.arguments

    if param_name not in args:
        return [], None

    value = args[param_name]

    if value is None:
        return [], None

    if isinstance(value, list):
        if not value:  # empty list
            return [], None

        # Convert all elements to strings
        result = []
        for item in value:
            if not isinstance(item, str):
                return None, ValueError(f"parameter {param_name} contains non-string element: {type(item).__name__}")
            result.append(item)
        return result, None

    return None, ValueError(f"parameter {param_name} could not be coerced to []string, got {type(value).__name__}")


def optional_pagination_params(request: CallToolRequest) -> Tuple[PaginationParams, Optional[Exception]]:
    """
    Returns pagination parameters from the request with defaults.
    Default page is 1, default per_page is 30.
    """
    page, err = optional_int_param_with_default(request, "page", 1)
    if err:
        return PaginationParams(), err

    per_page, err = optional_int_param_with_default(request, "perPage", 30)
    if err:
        return PaginationParams(), err

    after, err = optional_param(request, "after", str)
    if err:
        return PaginationParams(), err

    after = after or ""

    return PaginationParams(page=page, per_page=per_page, after=after), None


def optional_cursor_pagination_params(request: CallToolRequest) -> Tuple[CursorPaginationParams, Optional[Exception]]:
    """
    Returns cursor pagination parameters from the request.
    """
    per_page, err = optional_int_param_with_default(request, "perPage", 30)
    if err:
        return CursorPaginationParams(), err

    after, err = optional_param(request, "after", str)
    if err:
        return CursorPaginationParams(), err

    after = after or ""

    return CursorPaginationParams(per_page=per_page, after=after), None


def to_bool_ptr(b: bool) -> Optional[bool]:
    """Convert a bool to a boolean pointer."""
    return b


def to_string_ptr(s: str) -> Optional[str]:
    """Convert a string to a string pointer. Returns None if empty."""
    return s if s else None


def marshalled_text_result(data: Any) -> CallToolResult:
    """
    Create a CallToolResult with JSON-marshalled data.
    """
    try:
        json_data = json.dumps(data)
        return CallToolResult(type="text", text=json_data)
    except Exception as e:
        logger.error(f"Failed to marshal text result to JSON: {e}")
        return CallToolResult(type="error", error={"message": f"failed to marshal text result to json: {e}"})


class GitHubMCPServer:
    """
    GitHub MCP Server class - main server implementation.
    """

    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self.mcp_server = None

    def create_server(self) -> FastMCP:
        """
        Create a new GitHub MCP server instance.
        """
        self.mcp_server = FastMCP(name="github-mcp-server", version=self.version)
        return self.mcp_server
