"""
GitHub Repository Tools
Converted from github-mcp-server/pkg/github/repositories.go
"""

import json
import base64
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from mcp.types import Tool, CallToolRequest, CallToolResult
from mcp.server.fastmcp import FastMCP
from .server import (
    GetClientFn, TranslationHelperFunc, required_param, optional_param,
    optional_bool_param_with_default, optional_pagination_params,
    to_bool_ptr, marshalled_text_result
)
import logging

logger = logging.getLogger(__name__)

# Minimal types for GitHub API responses
class MinimalCommit:
    """Minimal representation of a GitHub commit."""
    def __init__(self, sha: str = "", message: str = "", author: Optional[Dict] = None,
                 committer: Optional[Dict] = None, url: str = "", html_url: str = "",
                 files: Optional[List] = None, stats: Optional[Dict] = None):
        self.sha = sha
        self.message = message
        self.author = author
        self.committer = committer
        self.url = url
        self.html_url = html_url
        self.files = files
        self.stats = stats

def convert_to_minimal_commit(commit: Any, include_diff: bool = False) -> MinimalCommit:
    """Convert a GitHub commit to minimal representation."""
    if not commit:
        return MinimalCommit()

    # Extract basic commit info
    sha = getattr(commit, 'sha', '')
    message = ''
    author = None
    committer = None
    url = getattr(commit, 'url', '')
    html_url = getattr(commit, 'html_url', '')

    if hasattr(commit, 'commit'):
        commit_data = commit.commit
        if hasattr(commit_data, 'message'):
            message = commit_data.message

        # Extract author info
        if hasattr(commit_data, 'author'):
            author_data = commit_data.author
            if author_data:
                author = {
                    'name': getattr(author_data, 'name', ''),
                    'email': getattr(author_data, 'email', ''),
                    'date': getattr(author_data, 'date', '').isoformat() if hasattr(author_data, 'date') and author_data.date else None
                }

        # Extract committer info
        if hasattr(commit_data, 'committer'):
            committer_data = commit_data.committer
            if committer_data:
                committer = {
                    'name': getattr(committer_data, 'name', ''),
                    'email': getattr(committer_data, 'email', ''),
                    'date': getattr(committer_data, 'date', '').isoformat() if hasattr(committer_data, 'date') and committer_data.date else None
                }

    files = None
    stats = None

    if include_diff:
        # Extract file changes and stats if requested
        if hasattr(commit, 'files'):
            files = []
            for file in commit.files or []:
                files.append({
                    'filename': getattr(file, 'filename', ''),
                    'status': getattr(file, 'status', ''),
                    'additions': getattr(file, 'additions', 0),
                    'deletions': getattr(file, 'deletions', 0),
                    'changes': getattr(file, 'changes', 0),
                    'patch': getattr(file, 'patch', '') if hasattr(file, 'patch') else None
                })

        if hasattr(commit, 'stats'):
            stats_data = commit.stats
            if stats_data:
                stats = {
                    'additions': getattr(stats_data, 'additions', 0),
                    'deletions': getattr(stats_data, 'deletions', 0),
                    'total': getattr(stats_data, 'total', 0)
                }

    return MinimalCommit(
        sha=sha,
        message=message,
        author=author,
        committer=committer,
        url=url,
        html_url=html_url,
        files=files,
        stats=stats
    )

def get_commit_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_commit tool."""
    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            sha, err = required_param(request, "sha", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            include_diff, err = optional_bool_param_with_default(request, "include_diff", True)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            client = get_client(ctx)
            try:
                commit = client.get_repo(f"{owner}/{repo}").get_commit(sha)
                minimal_commit = convert_to_minimal_commit(commit, include_diff)
                return marshalled_text_result(minimal_commit)
            except Exception as e:
                logger.error(f"Failed to get commit {sha}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get commit {sha}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_commit handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_commit",
        description=translator("TOOL_GET_COMMITS_DESCRIPTION", "Get details for a commit from a GitHub repository"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "sha": {"type": "string", "description": "Commit SHA, branch name, or tag name"},
                "include_diff": {"type": "boolean", "description": "Whether to include file diffs and stats", "default": True},
                "page": {"type": "number", "description": "Page number for pagination (min 1)", "minimum": 1},
                "perPage": {"type": "number", "description": "Results per page (min 1, max 100)", "minimum": 1, "maximum": 100}
            },
            "required": ["owner", "repo", "sha"]
        }
    )
    return tool, handler

def list_commits_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_commits tool."""
    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            sha, err = optional_param(request, "sha", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            author, err = optional_param(request, "author", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            per_page = pagination.per_page or 30
            client = get_client(ctx)

            try:
                repository = client.get_repo(f"{owner}/{repo}")
                commits = repository.get_commits(sha=sha, author=author, page=pagination.page, per_page=per_page)

                minimal_commits = []
                for commit in commits:
                    minimal_commits.append(convert_to_minimal_commit(commit, False))

                return marshalled_text_result(minimal_commits)
            except Exception as e:
                logger.error(f"Failed to list commits: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list commits: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_commits handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_commits",
        description=translator("TOOL_LIST_COMMITS_DESCRIPTION", "Get list of commits of a branch in a GitHub repository"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "sha": {"type": "string", "description": "Commit SHA, branch or tag name to list commits of"},
                "author": {"type": "string", "description": "Author username or email address to filter commits by"},
                "page": {"type": "number", "description": "Page number for pagination (min 1)", "minimum": 1},
                "perPage": {"type": "number", "description": "Results per page (min 1, max 100)", "minimum": 1, "maximum": 100}
            },
            "required": ["owner", "repo"]
        }
    )
    return tool, handler

def search_repositories_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the search_repositories tool."""
    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
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

            client = get_client(ctx)

            try:
                results = client.search_repositories(
                    query=query,
                    sort=sort or "best-match",
                    order=order or "desc",
                    page=pagination.page,
                    per_page=pagination.per_page
                )

                repos = []
                for repo in results:
                    repos.append({
                        'id': repo.id,
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'description': repo.description,
                        'html_url': repo.html_url,
                        'language': repo.language,
                        'stargazers_count': repo.stargazers_count,
                        'forks_count': repo.forks_count,
                        'owner': {
                            'login': repo.owner.login if repo.owner else None,
                            'type': repo.owner.type if repo.owner else None
                        } if repo.owner else None
                    })

                return marshalled_text_result(repos)
            except Exception as e:
                logger.error(f"Failed to search repositories: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to search repositories: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in search_repositories handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="search_repositories",
        description=translator("TOOL_SEARCH_REPOSITORIES_DESCRIPTION", "Search for GitHub repositories"),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "sort": {"type": "string", "description": "Sort field", "enum": ["best-match", "stars", "forks", "updated"]},
                "order": {"type": "string", "description": "Sort order", "enum": ["asc", "desc"]},
                "page": {"type": "number", "description": "Page number for pagination (min 1)", "minimum": 1},
                "perPage": {"type": "number", "description": "Results per page (min 1, max 100)", "minimum": 1, "maximum": 100}
            },
            "required": ["query"]
        }
    )
    return tool, handler

def get_file_contents_tool(get_client: GetClientFn, translator: TranslationHelperFunc, get_raw_client: Optional[Callable] = None) -> Tuple[Tool, Callable]:
    """Create the get_file_contents tool."""
    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            path, err = required_param(request, "path", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            ref, err = optional_param(request, "ref", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            client = get_client(ctx)

            try:
                repository = client.get_repo(f"{owner}/{repo}")

                if ref:
                    file_content = repository.get_contents(path, ref=ref)
                else:
                    file_content = repository.get_contents(path)

                if isinstance(file_content, list):
                    files = []
                    for item in file_content:
                        files.append({
                            'name': getattr(item, 'name', ''),
                            'path': getattr(item, 'path', ''),
                            'type': getattr(item, 'type', ''),
                            'size': getattr(item, 'size', 0),
                            'download_url': getattr(item, 'download_url', ''),
                        })
                    return marshalled_text_result({'files': files})
                else:
                    content = getattr(file_content, 'decoded_content', b'').decode('utf-8')
                    encoding = getattr(file_content, 'encoding', '')

                    if encoding == 'base64' and not content:
                        content = base64.b64decode(getattr(file_content, 'content', '')).decode('utf-8')

                    return marshalled_text_result({
                        'name': getattr(file_content, 'name', ''),
                        'path': getattr(file_content, 'path', ''),
                        'content': content,
                        'encoding': encoding,
                        'size': getattr(file_content, 'size', 0),
                        'sha': getattr(file_content, 'sha', ''),
                        'download_url': getattr(file_content, 'download_url', ''),
                    })

            except Exception as e:
                logger.error(f"Failed to get file contents for {path}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get file contents for {path}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_file_contents handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_file_contents",
        description=translator("TOOL_GET_FILE_CONTENTS_DESCRIPTION", "Get the contents of a file or list directory contents"),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "Path to file or directory"},
                "ref": {"type": "string", "description": "Branch name, tag, or commit SHA"}
            },
            "required": ["owner", "repo", "path"]
        }
    )
    return tool, handler

# Export the main functions for tool registration
def get_repository_tools(get_client: GetClientFn, get_raw_client: Optional[Callable] = None, translator: Optional[TranslationHelperFunc] = None) -> List[Tuple[Tool, Callable]]:
    """Get all repository-related tools."""
    if translator is None:
        translator = lambda key, default: default

    return [
        get_commit_tool(get_client, translator),
        list_commits_tool(get_client, translator),
        search_repositories_tool(get_client, translator),
        get_file_contents_tool(get_client, translator, get_raw_client),
    ]
