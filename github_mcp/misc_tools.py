"""
GitHub Miscellaneous Tools
Converted from github-mcp-server/pkg/github/ (notifications.go, gists.go, discussions.go)
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
def convert_to_notification(notification: Any) -> Dict[str, Any]:
    """Convert GitHub notification to dictionary format."""
    if not notification:
        return {}

    result = {
        'id': getattr(notification, 'id', ''),
        'unread': getattr(notification, 'unread', True),
        'reason': getattr(notification, 'reason', ''),
        'updated_at': getattr(notification, 'updated_at', '').isoformat() if hasattr(notification, 'updated_at') and notification.updated_at else None,
        'last_read_at': getattr(notification, 'last_read_at', '').isoformat() if hasattr(notification, 'last_read_at') and notification.last_read_at else None,
        'url': getattr(notification, 'url', ''),
    }

    # Extract subject information
    if hasattr(notification, 'subject') and notification.subject:
        result['subject'] = {
            'title': getattr(notification.subject, 'title', ''),
            'url': getattr(notification.subject, 'url', ''),
            'latest_comment_url': getattr(notification.subject, 'latest_comment_url', ''),
            'type': getattr(notification.subject, 'type', ''),
        }

    # Extract repository information
    if hasattr(notification, 'repository') and notification.repository:
        result['repository'] = {
            'id': getattr(notification.repository, 'id', 0),
            'name': getattr(notification.repository, 'name', ''),
            'full_name': getattr(notification.repository, 'full_name', ''),
            'html_url': getattr(notification.repository, 'html_url', ''),
        }

    return result


def convert_to_gist(gist: Any) -> Dict[str, Any]:
    """Convert GitHub gist to dictionary format."""
    if not gist:
        return {}

    result = {
        'id': getattr(gist, 'id', ''),
        'html_url': getattr(gist, 'html_url', ''),
        'public': getattr(gist, 'public', True),
        'created_at': getattr(gist, 'created_at', '').isoformat() if hasattr(gist, 'created_at') and gist.created_at else None,
        'updated_at': getattr(gist, 'updated_at', '').isoformat() if hasattr(gist, 'updated_at') and gist.updated_at else None,
        'description': getattr(gist, 'description', ''),
        'comments': getattr(gist, 'comments', 0),
    }

    # Extract owner information
    if hasattr(gist, 'owner') and gist.owner:
        result['owner'] = {
            'login': getattr(gist.owner, 'login', ''),
            'id': getattr(gist.owner, 'id', 0),
            'html_url': getattr(gist.owner, 'html_url', ''),
        }

    # Extract files information
    if hasattr(gist, 'files'):
        result['files'] = {}
        for filename, file_info in gist.files.items():
            result['files'][filename] = {
                'filename': getattr(file_info, 'filename', ''),
                'type': getattr(file_info, 'type', ''),
                'language': getattr(file_info, 'language', ''),
                'raw_url': getattr(file_info, 'raw_url', ''),
                'size': getattr(file_info, 'size', 0),
            }

    return result


def convert_to_discussion(discussion: Any) -> Dict[str, Any]:
    """Convert GitHub discussion to dictionary format."""
    if not discussion:
        return {}

    result = {
        'id': getattr(discussion, 'id', ''),
        'number': getattr(discussion, 'number', 0),
        'title': getattr(discussion, 'title', ''),
        'body': getattr(discussion, 'body', ''),
        'html_url': getattr(discussion, 'html_url', ''),
        'created_at': getattr(discussion, 'created_at', '').isoformat() if hasattr(discussion, 'created_at') and discussion.created_at else None,
        'updated_at': getattr(discussion, 'updated_at', '').isoformat() if hasattr(discussion, 'updated_at') and discussion.updated_at else None,
        'upvote_count': getattr(discussion, 'upvote_count', 0),
        'comments_count': getattr(discussion, 'comments_count', 0),
        'locked': getattr(discussion, 'locked', False),
        'state': getattr(discussion, 'state', ''),
    }

    # Extract author information
    if hasattr(discussion, 'author') and discussion.author:
        result['author'] = {
            'login': getattr(discussion.author, 'login', ''),
            'id': getattr(discussion.author, 'id', ''),
            'url': getattr(discussion.author, 'url', ''),
        }

    # Extract category information
    if hasattr(discussion, 'category') and discussion.category:
        result['category'] = {
            'id': getattr(discussion.category, 'id', ''),
            'name': getattr(discussion.category, 'name', ''),
            'description': getattr(discussion.category, 'description', ''),
            'emoji': getattr(discussion.category, 'emoji', ''),
        }

    return result


def list_notifications_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_notifications tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            all_notifications, err = optional_bool_param_with_default(request, "all", False)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            participating, err = optional_bool_param_with_default(request, "participating", False)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            since, err = optional_param(request, "since", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            before, err = optional_param(request, "before", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get notifications
                notifications = client.get_user().get_notifications(
                    all=all_notifications,
                    participating=participating,
                    since=since,
                    before=before,
                    page=pagination.page,
                    per_page=pagination.per_page
                )

                # Convert to list of notifications
                result = []
                for notification in notifications:
                    result.append(convert_to_notification(notification))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list notifications: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list notifications: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_notifications handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_notifications",
        description=translator("TOOL_LIST_NOTIFICATIONS_DESCRIPTION", "List GitHub notifications for the authenticated user"),
        inputSchema={
            "type": "object",
            "properties": {
                "all": {
                    "type": "boolean",
                    "description": "Include all notifications, not just unread ones",
                    "default": False
                },
                "participating": {
                    "type": "boolean",
                    "description": "Only include notifications in which the user is directly participating",
                    "default": False
                },
                "since": {
                    "type": "string",
                    "description": "Only show notifications updated after this timestamp (ISO 8601 format)"
                },
                "before": {
                    "type": "string",
                    "description": "Only show notifications updated before this timestamp (ISO 8601 format)"
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
            }
        }
    )

    return tool, handler


def list_gists_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_gists tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            since, err = optional_param(request, "since", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get gists
                gists = client.get_user().get_gists(since=since)

                # Convert to list of gists
                result = []
                for gist in gists:
                    result.append(convert_to_gist(gist))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list gists: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list gists: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_gists handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_gists",
        description=translator("TOOL_LIST_GISTS_DESCRIPTION", "List GitHub gists for the authenticated user"),
        inputSchema={
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "Only show gists updated after this timestamp (ISO 8601 format)"
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
            }
        }
    )

    return tool, handler


def create_gist_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the create_gist tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            files, err = required_param(request, "files", dict)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            description, err = optional_param(request, "description", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            public, err = optional_bool_param_with_default(request, "public", False)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Create the gist
                gist = client.get_user().create_gist(
                    public=public,
                    files=files,
                    description=description or ''
                )

                gist_dict = convert_to_gist(gist)
                return marshalled_text_result(gist_dict)

            except Exception as e:
                logger.error(f"Failed to create gist: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to create gist: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in create_gist handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="create_gist",
        description=translator("TOOL_CREATE_GIST_DESCRIPTION", "Create a new GitHub gist"),
        inputSchema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "object",
                    "description": "Files to include in the gist",
                    "additionalProperties": {
                        "type": "string"
                    }
                },
                "description": {
                    "type": "string",
                    "description": "Description of the gist"
                },
                "public": {
                    "type": "boolean",
                    "description": "Whether the gist should be public",
                    "default": False
                }
            },
            "required": ["files"]
        }
    )

    return tool, handler


def get_discussion_tool(get_gql_client: GetGQLClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_discussion tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            discussion_number, err = required_param(request, "discussion_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GraphQL client
            gql_client = get_gql_client(ctx)

            try:
                # This would need GraphQL implementation
                # For now, return a placeholder response
                return marshalled_text_result({
                    'message': 'Discussion retrieval requires GraphQL implementation',
                    'owner': owner,
                    'repo': repo,
                    'discussion_number': discussion_number
                })

            except Exception as e:
                logger.error(f"Failed to get discussion {discussion_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get discussion {discussion_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_discussion handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_discussion",
        description=translator("TOOL_GET_DISCUSSION_DESCRIPTION", "Get details for a GitHub discussion"),
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
                "discussion_number": {
                    "type": "integer",
                    "description": "Discussion number"
                }
            },
            "required": ["owner", "repo", "discussion_number"]
        }
    )

    return tool, handler


# Export the main functions for tool registration
def get_misc_tools(get_client: GetClientFn, get_gql_client: Optional[GetGQLClientFn] = None, translator: Optional[TranslationHelperFunc] = None) -> List[Tuple[Tool, Callable]]:
    """Get all miscellaneous tools."""
    if translator is None:
        translator = lambda key, default: default

    tools = [
        list_notifications_tool(get_client, translator),
        list_gists_tool(get_client, translator),
        create_gist_tool(get_client, translator),
    ]

    # Add GraphQL-based tools if GraphQL client is available
    if get_gql_client:
        tools.append(get_discussion_tool(get_gql_client, translator))

    return tools
