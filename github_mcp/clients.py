"""
GitHub MCP Clients - GitHub API client factory functions
Converted from github-mcp-server internal client creation logic
"""

import os
from typing import Any, Optional
from urllib.parse import urlparse, urljoin
import requests
from github import Github
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
    if not host or host == "github.com":
        # GitHub.com (dotcom)
        return {
            'base_url': "https://api.github.com/",
            'graphql_url': "https://api.github.com/graphql",
            'upload_url': "https://uploads.github.com/",
            'raw_url': "https://raw.githubusercontent.com/"
        }

    # Parse the host URL
    from urllib.parse import urlparse
    try:
        parsed = urlparse(host if "://" in host else f"https://{host}")

        # Ensure HTTPS for GitHub Enterprise Cloud
        if parsed.hostname and parsed.hostname.endswith("ghe.com"):
            if parsed.scheme != "https":
                raise ValueError("GitHub Enterprise Cloud URLs must use HTTPS")

        # GitHub Enterprise Server
        if parsed.hostname and parsed.hostname.endswith("github.com"):
            # This is still dotcom
            return {
                'base_url': "https://api.github.com/",
                'graphql_url': "https://api.github.com/graphql",
                'upload_url': "https://uploads.github.com/",
                'raw_url': "https://raw.githubusercontent.com/"
            }

        # GitHub Enterprise Server
        scheme = parsed.scheme or "https"
        hostname = parsed.hostname

        return {
            'base_url': f"{scheme}://{hostname}/api/v3/",
            'graphql_url': f"{scheme}://{hostname}/api/graphql",
            'upload_url': f"{scheme}://{hostname}/api/uploads/",
            'raw_url': f"{scheme}://{hostname}/raw/"
        }

    except Exception as e:
        logger.error(f"Failed to parse GitHub host '{host}': {e}")
        raise ValueError(f"Invalid GitHub host format: {host}")


def create_rest_client(config: GitHubClientConfig) -> Github:
    """
    Create a GitHub REST API client.
    """
    try:
        # Parse the API host
        api_urls = _parse_api_host(config.host)

        # Create the client
        client = Github(
            login_or_token=config.token,
            base_url=api_urls['base_url']
        )

        # Set user agent
        user_agent = f"github-mcp-server/{config.version}"
        if config.client_name and config.client_version:
            user_agent = f"{user_agent} ({config.client_name}/{config.client_version})"

        # Note: PyGithub doesn't expose direct user agent setting like go-github
        # We'll handle this through custom transport if needed

        logger.info(f"Created GitHub REST client for {config.host}")
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
    def factory(ctx=None) -> Github:
        return create_rest_client(config)

    return factory


def get_graphql_client_factory(config: GitHubClientConfig):
    """
    Return a factory function for creating GraphQL clients.
    """
    def factory(ctx=None) -> GraphQLClient:
        return create_graphql_client(config)

    return factory
