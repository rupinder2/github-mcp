"""
GitHub Pull Request Tools
Converted from github-mcp-server/pkg/github/pullrequests.go
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from mcp.types import Tool, CallToolRequest, CallToolResult
from mcp.server.fastmcp import FastMCP
from .server import (
    GetClientFn, GetGQLClientFn, TranslationHelperFunc, required_param, optional_param,
    optional_bool_param_with_default, optional_pagination_params,
    to_bool_ptr, marshalled_text_result
)
from .clients import GraphQLClient
import logging

logger = logging.getLogger(__name__)

# Type definitions for GitHub API responses
class PullRequestFile:
    """Represents a file changed in a pull request."""
    def __init__(self, filename: str = "", status: str = "", additions: int = 0,
                 deletions: int = 0, changes: int = 0, patch: Optional[str] = None):
        self.filename = filename
        self.status = status
        self.additions = additions
        self.deletions = deletions
        self.changes = changes
        self.patch = patch


def convert_to_pull_request(pr: Any) -> Dict[str, Any]:
    """Convert GitHub pull request to dictionary format."""
    if not pr:
        return {}

    result = {
        'id': getattr(pr, 'id', 0),
        'number': getattr(pr, 'number', 0),
        'title': getattr(pr, 'title', ''),
        'body': getattr(pr, 'body', ''),
        'state': getattr(pr, 'state', ''),
        'html_url': getattr(pr, 'html_url', ''),
        'created_at': getattr(pr, 'created_at', '').isoformat() if hasattr(pr, 'created_at') and pr.created_at else None,
        'updated_at': getattr(pr, 'updated_at', '').isoformat() if hasattr(pr, 'updated_at') and pr.updated_at else None,
        'closed_at': getattr(pr, 'closed_at', '').isoformat() if hasattr(pr, 'closed_at') and pr.closed_at else None,
        'merged_at': getattr(pr, 'merged_at', '').isoformat() if hasattr(pr, 'merged_at') and pr.merged_at else None,
        'mergeable': getattr(pr, 'mergeable', None),
        'mergeable_state': getattr(pr, 'mergeable_state', ''),
        'merged': getattr(pr, 'merged', False),
        'merge_commit_sha': getattr(pr, 'merge_commit_sha', ''),
        'draft': getattr(pr, 'draft', False),
    }

    # Extract head and base branch information
    if hasattr(pr, 'head') and pr.head:
        result['head'] = {
            'ref': getattr(pr.head, 'ref', ''),
            'sha': getattr(pr.head, 'sha', ''),
            'repo': {
                'name': getattr(pr.head.repo, 'name', '') if pr.head.repo else '',
                'full_name': getattr(pr.head.repo, 'full_name', '') if pr.head.repo else '',
            } if pr.head.repo else {}
        }

    if hasattr(pr, 'base') and pr.base:
        result['base'] = {
            'ref': getattr(pr.base, 'ref', ''),
            'sha': getattr(pr.base, 'sha', ''),
            'repo': {
                'name': getattr(pr.base.repo, 'name', '') if pr.base.repo else '',
                'full_name': getattr(pr.base.repo, 'full_name', '') if pr.base.repo else '',
            } if pr.base.repo else {}
        }

    # Extract user information
    if hasattr(pr, 'user') and pr.user:
        result['user'] = {
            'login': getattr(pr.user, 'login', ''),
            'id': getattr(pr.user, 'id', 0),
            'html_url': getattr(pr.user, 'html_url', ''),
            'type': getattr(pr.user, 'type', ''),
        }

    # Extract labels
    if hasattr(pr, 'labels'):
        result['labels'] = []
        for label in pr.labels or []:
            result['labels'].append({
                'name': getattr(label, 'name', ''),
                'color': getattr(label, 'color', ''),
                'description': getattr(label, 'description', ''),
            })

    return result


def convert_to_pr_file(file: Any) -> Dict[str, Any]:
    """Convert GitHub pull request file to dictionary format."""
    if not file:
        return {}

    return {
        'filename': getattr(file, 'filename', ''),
        'status': getattr(file, 'status', ''),
        'additions': getattr(file, 'additions', 0),
        'deletions': getattr(file, 'deletions', 0),
        'changes': getattr(file, 'changes', 0),
        'patch': getattr(file, 'patch', '') if hasattr(file, 'patch') else None,
        'blob_url': getattr(file, 'blob_url', ''),
        'raw_url': getattr(file, 'raw_url', ''),
    }


def get_pull_request_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_pull_request tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pull_number, err = required_param(request, "pull_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get the pull request
                repository = client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pull_number)
                pr_dict = convert_to_pull_request(pr)
                return marshalled_text_result(pr_dict)

            except Exception as e:
                logger.error(f"Failed to get pull request {pull_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get pull request {pull_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_pull_request handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_pull_request",
        description=translator("TOOL_GET_PULL_REQUEST_DESCRIPTION", "Get details for a GitHub pull request"),
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
                "pull_number": {
                    "type": "integer",
                    "description": "Pull request number"
                }
            },
            "required": ["owner", "repo", "pull_number"]
        }
    )

    return tool, handler


def list_pull_requests_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_pull_requests tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            state, err = optional_param(request, "state", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            head, err = optional_param(request, "head", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            base, err = optional_param(request, "base", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            sort, err = optional_param(request, "sort", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            direction, err = optional_param(request, "direction", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get pull requests
                repository = client.get_repo(f"{owner}/{repo}")

                # Prepare parameters
                params = {}
                if state:
                    params['state'] = state
                if head:
                    params['head'] = head
                if base:
                    params['base'] = base
                if sort:
                    params['sort'] = sort
                if direction:
                    params['direction'] = direction

                pulls = repository.get_pulls(**params)
                paginated_pulls = pulls.get_page(pagination.page - 1) if pagination.page > 1 else list(pulls[:pagination.per_page])

                # Convert to list of pull requests
                result = []
                for pr in paginated_pulls:
                    result.append(convert_to_pull_request(pr))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list pull requests: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list pull requests: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_pull_requests handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_pull_requests",
        description=translator("TOOL_LIST_PULL_REQUESTS_DESCRIPTION", "List pull requests for a GitHub repository"),
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
                "state": {
                    "type": "string",
                    "description": "Pull request state",
                    "enum": ["open", "closed", "all"]
                },
                "head": {
                    "type": "string",
                    "description": "Filter by head branch"
                },
                "base": {
                    "type": "string",
                    "description": "Filter by base branch"
                },
                "sort": {
                    "type": "string",
                    "description": "Sort field",
                    "enum": ["created", "updated", "popularity", "long-running"]
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction",
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
            "required": ["owner", "repo"]
        }
    )

    return tool, handler


def create_pull_request_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the create_pull_request tool."""

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

            head, err = required_param(request, "head", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            base, err = required_param(request, "base", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            body, err = optional_param(request, "body", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            draft, err = optional_bool_param_with_default(request, "draft", False)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Create the pull request
                repository = client.get_repo(f"{owner}/{repo}")
                pr = repository.create_pull(
                    title=title,
                    body=body or '',
                    head=head,
                    base=base,
                    draft=draft
                )

                pr_dict = convert_to_pull_request(pr)
                return marshalled_text_result(pr_dict)

            except Exception as e:
                logger.error(f"Failed to create pull request: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to create pull request: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in create_pull_request handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="create_pull_request",
        description=translator("TOOL_CREATE_PULL_REQUEST_DESCRIPTION", "Create a new GitHub pull request"),
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
                    "description": "Pull request title"
                },
                "head": {
                    "type": "string",
                    "description": "Head branch name"
                },
                "base": {
                    "type": "string",
                    "description": "Base branch name"
                },
                "body": {
                    "type": "string",
                    "description": "Pull request body"
                },
                "draft": {
                    "type": "boolean",
                    "description": "Whether to create a draft pull request",
                    "default": False
                }
            },
            "required": ["owner", "repo", "title", "head", "base"]
        }
    )

    return tool, handler


def merge_pull_request_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the merge_pull_request tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pull_number, err = required_param(request, "pull_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            commit_title, err = optional_param(request, "commit_title", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            commit_message, err = optional_param(request, "commit_message", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            merge_method, err = optional_param(request, "merge_method", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Merge the pull request
                repository = client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pull_number)

                # Prepare merge options
                merge_options = {}
                if commit_title:
                    merge_options['commit_title'] = commit_title
                if commit_message:
                    merge_options['commit_message'] = commit_message
                if merge_method:
                    merge_options['merge_method'] = merge_method
                else:
                    merge_options['merge_method'] = 'merge'

                result = pr.merge(**merge_options)

                if result.merged:
                    return marshalled_text_result({
                        'merged': True,
                        'message': 'Pull request merged successfully',
                        'merge_commit_sha': result.sha
                    })
                else:
                    return CallToolResult(type="error", error={"message": "Failed to merge pull request"})

            except Exception as e:
                logger.error(f"Failed to merge pull request {pull_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to merge pull request {pull_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in merge_pull_request handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="merge_pull_request",
        description=translator("TOOL_MERGE_PULL_REQUEST_DESCRIPTION", "Merge a GitHub pull request"),
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
                "pull_number": {
                    "type": "integer",
                    "description": "Pull request number"
                },
                "commit_title": {
                    "type": "string",
                    "description": "Title for the merge commit"
                },
                "commit_message": {
                    "type": "string",
                    "description": "Message for the merge commit"
                },
                "merge_method": {
                    "type": "string",
                    "description": "Merge method to use",
                    "enum": ["merge", "squash", "rebase"]
                }
            },
            "required": ["owner", "repo", "pull_number"]
        }
    )

    return tool, handler


def get_pull_request_files_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_pull_request_files tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pull_number, err = required_param(request, "pull_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get pull request files
                repository = client.get_repo(f"{owner}/{repo}")
                pr = repository.get_pull(pull_number)
                files = pr.get_files()

                # Convert to list of files
                result = []
                for file in files:
                    result.append(convert_to_pr_file(file))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to get pull request files for {pull_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get pull request files for {pull_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_pull_request_files handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_pull_request_files",
        description=translator("TOOL_GET_PULL_REQUEST_FILES_DESCRIPTION", "Get files changed in a GitHub pull request"),
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
                "pull_number": {
                    "type": "integer",
                    "description": "Pull request number"
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
            "required": ["owner", "repo", "pull_number"]
        }
    )

    return tool, handler


# Export the main functions for tool registration
def get_pull_request_tools(get_client: GetClientFn, get_gql_client: Optional[GetGQLClientFn] = None, translator: Optional[TranslationHelperFunc] = None) -> List[Tuple[Tool, Callable]]:
    """Get all pull request-related tools."""
    if translator is None:
        translator = lambda key, default: default

    tools = [
        get_pull_request_tool(get_client, translator),
        list_pull_requests_tool(get_client, translator),
        get_pull_request_files_tool(get_client, translator),
    ]

    # Add write tools (these require write permissions)
    write_tools = [
        create_pull_request_tool(get_client, translator),
        merge_pull_request_tool(get_client, translator),
    ]

    tools.extend(write_tools)

    return tools
