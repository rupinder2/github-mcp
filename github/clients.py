"""
GitHub MCP Clients - GitHub API client factory functions
Converted from github-mcp-server internal client creation logic
"""

import os
from typing import Any, Optional
from urllib.parse import urlparse, urljoin
import requests
import github as gh
import logging

logger = logging.getLogger(__name__)


class GitHubClientConfig:
    """Configuration for GitHub client creation."""

    def __init__(
        self,
        token: str,
        host: str = "github.com",
        version: str = "1.0.0",
        client_name: Optional[str] = None,
        client_version: Optional[str] = None
    ):
        self.token = token
        self.host = host
        self.version = version
        self.client_name = client_name
        self.client_version = client_version


def _parse_api_host(host: str) -> dict:
    """
    Parse the GitHub host and return API URLs.
    Similar to the Go implementation's parseAPIHost function.
    """
    if not host:
        host = "github.com"

    # Handle GitHub Enterprise vs github.com
    if host == "github.com":
        base_url = "https://api.github.com/"
        graphql_url = "https://api.github.com/graphql"
        upload_url = "https://uploads.github.com/"
    else:
        # GitHub Enterprise
        scheme = "https"
        if host.startswith("http://"):
            scheme = "http"
            host = host[7:]
        elif host.startswith("https://"):
            host = host[8:]

        base_url = f"{scheme}://{host}/api/v3/"
        graphql_url = f"{scheme}://{host}/api/graphql"
        upload_url = f"{scheme}://{host}/api/uploads/"

    return {
        'base_url': base_url,
        'graphql_url': graphql_url,
        'upload_url': upload_url
    }


def create_rest_client(config: GitHubClientConfig) -> gh.Github:
    """
    Create a GitHub REST API client.
    """
    try:
        # Parse the API host
        api_urls = _parse_api_host(config.host)

        # Create the client
        client = gh.Github(
            login_or_token=config.token,
            base_url=api_urls['base_url']
        )

        # Set user agent
        user_agent = f"github-mcp-server/{config.version}"
        if config.client_name and config.client_version:
            user_agent = f"{user_agent} ({config.client_name}/{config.client_version})"

        # Note: PyGithub doesn't expose direct user agent setting like go-github
        # We'll need to handle this through request headers if needed

        return client

    except Exception as e:
        logger.error(f"Failed to create GitHub REST client: {e}")
        raise


def create_graphql_client(config: GitHubClientConfig) -> Any:
    """
    Create a GitHub GraphQL API client.
    For Python, we'll use requests directly with GraphQL queries.
    """
    try:
        api_urls = _parse_api_host(config.host)

        # Create a session with authentication
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {config.token}',
            'Content-Type': 'application/json'
        })

        # Set user agent
        user_agent = f"github-mcp-server/{config.version}"
        if config.client_name and config.client_version:
            user_agent = f"{user_agent} ({config.client_name}/{config.client_version})"

        session.headers.update({'User-Agent': user_agent})

        # Return a simple wrapper that can execute GraphQL queries
        return GraphQLClient(session, api_urls['graphql_url'])

    except Exception as e:
        logger.error(f"Failed to create GitHub GraphQL client: {e}")
        raise


class GraphQLClient:
    """Simple GraphQL client wrapper."""

    def __init__(self, session: requests.Session, endpoint: str):
        self.session = session
        self.endpoint = endpoint

    def execute(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query."""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        response = self.session.post(self.endpoint, json=payload)
        response.raise_for_status()

        result = response.json()
        if 'errors' in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result


def get_rest_client_factory(config: GitHubClientConfig):
    """
    Return a factory function for creating REST clients.
    """
    def factory(ctx=None) -> gh.Github:
        return create_rest_client(config)

    return factory


def get_graphql_client_factory(config: GitHubClientConfig):
    """
    Return a factory function for creating GraphQL clients.
    """
    def factory(ctx=None) -> GraphQLClient:
        return create_graphql_client(config)

    return factory
