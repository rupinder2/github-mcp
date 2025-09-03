"""
GitHub Issues Tools
Converted from github-mcp-server/pkg/github/issues.go
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from mcp.types import Tool, CallToolRequest, CallToolResult
from mcp.server.fastmcp import FastMCP
from .server import (
    GetClientFn, GetGQLClientFn, TranslationHelperFunc, required_param, optional_param,
    optional_bool_param_with_default, optional_pagination_params, optional_string_array_param,
    to_bool_ptr, marshalled_text_result, CursorPaginationParams
)
from .clients import GraphQLClient
import logging

logger = logging.getLogger(__name__)

# Type definitions for GitHub API responses
class IssueFragment:
    """Represents a fragment of an issue from GraphQL API."""
    def __init__(self, number: int = 0, title: str = "", body: str = "", state: str = "",
                 database_id: int = 0, author: Optional[Dict] = None,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None,
                 labels: Optional[List[Dict]] = None, comments_count: int = 0):
        self.number = number
        self.title = title
        self.body = body
        self.state = state
        self.database_id = database_id
        self.author = author
        self.created_at = created_at
        self.updated_at = updated_at
        self.labels = labels or []
        self.comments_count = comments_count


class IssueQueryFragment:
    """Fragment containing issues and pagination info."""
    def __init__(self, nodes: Optional[List[IssueFragment]] = None,
                 page_info: Optional[Dict] = None, total_count: int = 0):
        self.nodes = nodes or []
        self.page_info = page_info or {}
        self.total_count = total_count


def convert_to_issue(issue: Any) -> Dict[str, Any]:
    """Convert GitHub issue to dictionary format."""
    if not issue:
        return {}

    # Extract basic issue information
    result = {
        'id': getattr(issue, 'id', 0),
        'number': getattr(issue, 'number', 0),
        'title': getattr(issue, 'title', ''),
        'body': getattr(issue, 'body', ''),
        'state': getattr(issue, 'state', ''),
        'html_url': getattr(issue, 'html_url', ''),
        'created_at': getattr(issue, 'created_at', '').isoformat() if hasattr(issue, 'created_at') and issue.created_at else None,
        'updated_at': getattr(issue, 'updated_at', '').isoformat() if hasattr(issue, 'updated_at') and issue.updated_at else None,
        'closed_at': getattr(issue, 'closed_at', '').isoformat() if hasattr(issue, 'closed_at') and issue.closed_at else None,
    }

    # Extract user information
    if hasattr(issue, 'user') and issue.user:
        result['user'] = {
            'login': getattr(issue.user, 'login', ''),
            'id': getattr(issue.user, 'id', 0),
            'html_url': getattr(issue.user, 'html_url', ''),
            'type': getattr(issue.user, 'type', ''),
        }

    # Extract labels
    if hasattr(issue, 'labels'):
        result['labels'] = []
        for label in issue.labels or []:
            result['labels'].append({
                'name': getattr(label, 'name', ''),
                'color': getattr(label, 'color', ''),
                'description': getattr(label, 'description', ''),
            })

    # Extract assignee information
    if hasattr(issue, 'assignee') and issue.assignee:
        result['assignee'] = {
            'login': getattr(issue.assignee, 'login', ''),
            'id': getattr(issue.assignee, 'id', 0),
            'html_url': getattr(issue.assignee, 'html_url', ''),
        }

    # Extract assignees list
    if hasattr(issue, 'assignees'):
        result['assignees'] = []
        for assignee in issue.assignees or []:
            result['assignees'].append({
                'login': getattr(assignee, 'login', ''),
                'id': getattr(assignee, 'id', 0),
                'html_url': getattr(assignee, 'html_url', ''),
            })

    # Extract milestone information
    if hasattr(issue, 'milestone') and issue.milestone:
        result['milestone'] = {
            'title': getattr(issue.milestone, 'title', ''),
            'number': getattr(issue.milestone, 'number', 0),
            'state': getattr(issue.milestone, 'state', ''),
        }

    return result


def convert_to_issue_comment(comment: Any) -> Dict[str, Any]:
    """Convert GitHub issue comment to dictionary format."""
    if not comment:
        return {}

    result = {
        'id': getattr(comment, 'id', 0),
        'body': getattr(comment, 'body', ''),
        'html_url': getattr(comment, 'html_url', ''),
        'created_at': getattr(comment, 'created_at', '').isoformat() if hasattr(comment, 'created_at') and comment.created_at else None,
        'updated_at': getattr(comment, 'updated_at', '').isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else None,
    }

    # Extract user information
    if hasattr(comment, 'user') and comment.user:
        result['user'] = {
            'login': getattr(comment.user, 'login', ''),
            'id': getattr(comment.user, 'id', 0),
            'html_url': getattr(comment.user, 'html_url', ''),
            'type': getattr(comment.user, 'type', ''),
        }

    return result


def get_issue_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_issue tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            issue_number, err = required_param(request, "issue_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get the issue
                issue = client.get_repo(f"{owner}/{repo}").get_issue(issue_number)
                issue_dict = convert_to_issue(issue)
                return marshalled_text_result(issue_dict)

            except Exception as e:
                logger.error(f"Failed to get issue {issue_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get issue {issue_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_issue handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_issue",
        description=translator("TOOL_GET_ISSUE_DESCRIPTION", "Get details for a GitHub issue"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number"
                }
            },
            "required": ["owner", "repo", "issue_number"]
        }
    )

    return tool, handler


def search_issues_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the search_issues tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            query, err = required_param(request, "query", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            sort, err = optional_param(request, "sort", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            order, err = optional_param(request, "order", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Search issues
                issues = client.search_issues(
                    query=query,
                    sort=sort or "best-match",
                    order=order or "desc",
                    page=pagination.page,
                    per_page=pagination.per_page
                )

                # Convert to list of issues
                result = []
                for issue in issues:
                    result.append(convert_to_issue(issue))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to search issues: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to search issues: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in search_issues handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="search_issues",
        description=translator("TOOL_SEARCH_ISSUES_DESCRIPTION", "Search for GitHub issues using keywords, qualifiers, and operators"),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (supports GitHub search syntax)"
                },
                "sort": {
                    "type": "string",
                    "description": "Sort field",
                    "enum": ["best-match", "comments", "created", "updated"]
                },
                "order": {
                    "type": "string",
                    "description": "Sort order",
                    "enum": ["asc", "desc"]
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (min 1)",
                    "minimum": 1
                },
                "perPage": {
                    "type": "number",
                    "description": "Results per page for pagination (min 1, max 100)",
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["query"]
        }
    )

    return tool, handler


def create_issue_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the create_issue tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            title, err = required_param(request, "title", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            body, err = optional_param(request, "body", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            labels, err = optional_string_array_param(request, "labels")
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            assignees, err = optional_string_array_param(request, "assignees")
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Create the issue
                repository = client.get_repo(f"{owner}/{repo}")

                # Prepare issue data
                issue_data = {
                    'title': title,
                    'body': body or '',
                }

                if labels:
                    issue_data['labels'] = labels
                if assignees:
                    issue_data['assignees'] = assignees

                issue = repository.create_issue(**issue_data)
                issue_dict = convert_to_issue(issue)
                return marshalled_text_result(issue_dict)

            except Exception as e:
                logger.error(f"Failed to create issue: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to create issue: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in create_issue handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="create_issue",
        description=translator("TOOL_CREATE_ISSUE_DESCRIPTION", "Create a new GitHub issue"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "title": {
                    "type": "string",
                    "description": "Issue title"
                },
                "body": {
                    "type": "string",
                    "description": "Issue body (optional)"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names to assign to the issue"
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of usernames to assign to the issue"
                }
            },
            "required": ["owner", "repo", "title"]
        }
    )

    return tool, handler


def update_issue_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the update_issue tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            issue_number, err = required_param(request, "issue_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            title, err = optional_param(request, "title", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            body, err = optional_param(request, "body", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            state, err = optional_param(request, "state", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            labels, err = optional_string_array_param(request, "labels")
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            assignees, err = optional_string_array_param(request, "assignees")
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get and update the issue
                repository = client.get_repo(f"{owner}/{repo}")
                issue = repository.get_issue(issue_number)

                # Prepare update data
                update_data = {}
                if title is not None:
                    update_data['title'] = title
                if body is not None:
                    update_data['body'] = body
                if state is not None:
                    update_data['state'] = state
                if labels is not None:
                    update_data['labels'] = labels
                if assignees is not None:
                    update_data['assignees'] = assignees

                if update_data:
                    issue.edit(**update_data)

                # Get updated issue
                updated_issue = repository.get_issue(issue_number)
                issue_dict = convert_to_issue(updated_issue)
                return marshalled_text_result(issue_dict)

            except Exception as e:
                logger.error(f"Failed to update issue {issue_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to update issue {issue_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in update_issue handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="update_issue",
        description=translator("TOOL_UPDATE_ISSUE_DESCRIPTION", "Update an existing GitHub issue"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number"
                },
                "title": {
                    "type": "string",
                    "description": "New issue title"
                },
                "body": {
                    "type": "string",
                    "description": "New issue body"
                },
                "state": {
                    "type": "string",
                    "description": "New issue state",
                    "enum": ["open", "closed"]
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names to assign to the issue"
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of usernames to assign to the issue"
                }
            },
            "required": ["owner", "repo", "issue_number"]
        }
    )

    return tool, handler


def get_issue_comments_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_issue_comments tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            issue_number, err = required_param(request, "issue_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get issue comments
                repository = client.get_repo(f"{owner}/{repo}")
                issue = repository.get_issue(issue_number)
                comments = issue.get_comments(page=pagination.page, per_page=pagination.per_page)

                # Convert to list of comments
                result = []
                for comment in comments:
                    result.append(convert_to_issue_comment(comment))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to get issue comments for {issue_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get issue comments for {issue_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_issue_comments handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_issue_comments",
        description=translator("TOOL_GET_ISSUE_COMMENTS_DESCRIPTION", "Get comments for a GitHub issue"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number"
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (min 1)",
                    "minimum": 1
                },
                "perPage": {
                    "type": "number",
                    "description": "Results per page for pagination (min 1, max 100)",
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["owner", "repo", "issue_number"]
        }
    )

    return tool, handler


def add_issue_comment_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the add_issue_comment tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            issue_number, err = required_param(request, "issue_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            body, err = required_param(request, "body", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Add comment to issue
                repository = client.get_repo(f"{owner}/{repo}")
                issue = repository.get_issue(issue_number)
                comment = issue.create_comment(body)

                comment_dict = convert_to_issue_comment(comment)
                return marshalled_text_result(comment_dict)

            except Exception as e:
                logger.error(f"Failed to add comment to issue {issue_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to add comment to issue {issue_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in add_issue_comment handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="add_issue_comment",
        description=translator("TOOL_ADD_ISSUE_COMMENT_DESCRIPTION", "Add a comment to a GitHub issue"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number"
                },
                "body": {
                    "type": "string",
                    "description": "Comment body"
                }
            },
            "required": ["owner", "repo", "issue_number", "body"]
        }
    )

    return tool, handler


# Export the main functions for tool registration
def get_issue_tools(get_client: GetClientFn, get_gql_client: Optional[GetGQLClientFn] = None, translator: Optional[TranslationHelperFunc] = None) -> List[Tuple[Tool, Callable]]:
    """Get all issue-related tools."""
    if translator is None:
        translator = lambda key, default: default

    tools = [
        get_issue_tool(get_client, translator),
        search_issues_tool(get_client, translator),
        create_issue_tool(get_client, translator),
        update_issue_tool(get_client, translator),
        get_issue_comments_tool(get_client, translator),
        add_issue_comment_tool(get_client, translator),
    ]

    # Add GraphQL-based tools if GraphQL client is available
    if get_gql_client:
        # These would need GraphQL implementations
        pass

    return tools
