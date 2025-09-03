"""
GitHub Security Tools
Converted from github-mcp-server/pkg/github/ (code_scanning.go, secret_scanning.go, dependabot.go, security_advisories.go)
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from mcp.types import Tool, CallToolRequest, CallToolResult
from mcp.server.fastmcp import FastMCP
from .server import (
    GetClientFn, TranslationHelperFunc, required_param, optional_param,
    optional_pagination_params, marshalled_text_result
)
from .clients import GraphQLClient
import logging

logger = logging.getLogger(__name__)

# Type definitions for GitHub API responses
def convert_to_dependabot_alert(alert: Any) -> Dict[str, Any]:
    """Convert GitHub Dependabot alert to dictionary format."""
    if not alert:
        return {}

    result = {
        'number': getattr(alert, 'number', 0),
        'state': getattr(alert, 'state', ''),
        'dependency': {
            'package': {
                'ecosystem': getattr(alert.dependency.package, 'ecosystem', '') if hasattr(alert, 'dependency') and alert.dependency and hasattr(alert.dependency, 'package') else '',
                'name': getattr(alert.dependency.package, 'name', '') if hasattr(alert, 'dependency') and alert.dependency and hasattr(alert.dependency, 'package') else '',
            } if hasattr(alert, 'dependency') and alert.dependency else {}
        } if hasattr(alert, 'dependency') else {},
        'security_advisory': {
            'ghsa_id': getattr(alert.security_advisory, 'ghsa_id', '') if hasattr(alert, 'security_advisory') and alert.security_advisory else '',
            'cve_id': getattr(alert.security_advisory, 'cve_id', '') if hasattr(alert, 'security_advisory') and alert.security_advisory else '',
            'summary': getattr(alert.security_advisory, 'summary', '') if hasattr(alert, 'security_advisory') and alert.security_advisory else '',
            'description': getattr(alert.security_advisory, 'description', '') if hasattr(alert, 'security_advisory') and alert.security_advisory else '',
            'severity': getattr(alert.security_advisory, 'severity', '') if hasattr(alert, 'security_advisory') and alert.security_advisory else '',
            'cvss': {
                'score': getattr(alert.security_advisory.cvss, 'score', 0.0) if hasattr(alert, 'security_advisory') and alert.security_advisory and hasattr(alert.security_advisory, 'cvss') and alert.security_advisory.cvss else 0.0,
                'vector_string': getattr(alert.security_advisory.cvss, 'vector_string', '') if hasattr(alert, 'security_advisory') and alert.security_advisory and hasattr(alert.security_advisory, 'cvss') and alert.security_advisory.cvss else '',
            } if hasattr(alert, 'security_advisory') and alert.security_advisory and hasattr(alert.security_advisory, 'cvss') else {},
        } if hasattr(alert, 'security_advisory') else {},
        'created_at': getattr(alert, 'created_at', '').isoformat() if hasattr(alert, 'created_at') and alert.created_at else None,
        'updated_at': getattr(alert, 'updated_at', '').isoformat() if hasattr(alert, 'updated_at') and alert.updated_at else None,
        'html_url': getattr(alert, 'html_url', ''),
    }

    return result


def convert_to_code_scanning_alert(alert: Any) -> Dict[str, Any]:
    """Convert GitHub Code Scanning alert to dictionary format."""
    if not alert:
        return {}

    result = {
        'number': getattr(alert, 'number', 0),
        'state': getattr(alert, 'state', ''),
        'severity': getattr(alert, 'severity', ''),
        'rule': {
            'id': getattr(alert.rule, 'id', '') if hasattr(alert, 'rule') and alert.rule else '',
            'name': getattr(alert.rule, 'name', '') if hasattr(alert, 'rule') and alert.rule else '',
            'description': getattr(alert.rule, 'description', '') if hasattr(alert, 'rule') and alert.rule else '',
        } if hasattr(alert, 'rule') else {},
        'tool': {
            'name': getattr(alert.tool, 'name', '') if hasattr(alert, 'tool') and alert.tool else '',
            'version': getattr(alert.tool, 'version', '') if hasattr(alert, 'tool') and alert.tool else '',
        } if hasattr(alert, 'tool') else {},
        'created_at': getattr(alert, 'created_at', '').isoformat() if hasattr(alert, 'created_at') and alert.created_at else None,
        'updated_at': getattr(alert, 'updated_at', '').isoformat() if hasattr(alert, 'updated_at') and alert.updated_at else None,
        'html_url': getattr(alert, 'html_url', ''),
    }

    return result


def convert_to_secret_scanning_alert(alert: Any) -> Dict[str, Any]:
    """Convert GitHub Secret Scanning alert to dictionary format."""
    if not alert:
        return {}

    result = {
        'number': getattr(alert, 'number', 0),
        'state': getattr(alert, 'state', ''),
        'secret_type': getattr(alert, 'secret_type', ''),
        'secret': getattr(alert, 'secret', ''),
        'created_at': getattr(alert, 'created_at', '').isoformat() if hasattr(alert, 'created_at') and alert.created_at else None,
        'updated_at': getattr(alert, 'updated_at', '').isoformat() if hasattr(alert, 'updated_at') and alert.updated_at else None,
        'html_url': getattr(alert, 'html_url', ''),
    }

    return result


def convert_to_security_advisory(advisory: Any) -> Dict[str, Any]:
    """Convert GitHub Security Advisory to dictionary format."""
    if not advisory:
        return {}

    result = {
        'ghsa_id': getattr(advisory, 'ghsa_id', ''),
        'cve_id': getattr(advisory, 'cve_id', ''),
        'summary': getattr(advisory, 'summary', ''),
        'description': getattr(advisory, 'description', ''),
        'severity': getattr(advisory, 'severity', ''),
        'cvss': {
            'score': getattr(advisory.cvss, 'score', 0.0) if hasattr(advisory, 'cvss') and advisory.cvss else 0.0,
            'vector_string': getattr(advisory.cvss, 'vector_string', '') if hasattr(advisory, 'cvss') and advisory.cvss else '',
        } if hasattr(advisory, 'cvss') else {},
        'cwes': [],
        'published_at': getattr(advisory, 'published_at', '').isoformat() if hasattr(advisory, 'published_at') and advisory.published_at else None,
        'updated_at': getattr(advisory, 'updated_at', '').isoformat() if hasattr(advisory, 'updated_at') and advisory.updated_at else None,
        'html_url': getattr(advisory, 'html_url', ''),
    }

    # Extract CWEs if available
    if hasattr(advisory, 'cwes'):
        result['cwes'] = [{'cwe_id': cwe.cwe_id, 'name': cwe.name} for cwe in advisory.cwes or []]

    return result


def get_dependabot_alert_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_dependabot_alert tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            alert_number, err = required_param(request, "alert_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get Dependabot alert
                repository = client.get_repo(f"{owner}/{repo}")
                alert = repository.get_dependabot_alert(alert_number)
                alert_dict = convert_to_dependabot_alert(alert)
                return marshalled_text_result(alert_dict)

            except Exception as e:
                logger.error(f"Failed to get Dependabot alert {alert_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get Dependabot alert {alert_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_dependabot_alert handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_dependabot_alert",
        description=translator("TOOL_GET_DEPENDABOT_ALERT_DESCRIPTION", "Get details for a Dependabot security alert"),
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
                "alert_number": {
                    "type": "integer",
                    "description": "Dependabot alert number"
                }
            },
            "required": ["owner", "repo", "alert_number"]
        }
    )

    return tool, handler


def list_dependabot_alerts_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_dependabot_alerts tool."""

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

            severity, err = optional_param(request, "severity", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            ecosystem, err = optional_param(request, "ecosystem", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get Dependabot alerts
                repository = client.get_repo(f"{owner}/{repo}")
                alerts = repository.get_dependabot_alerts()

                # Convert to list of alerts
                result = []
                for alert in alerts:
                    result.append(convert_to_dependabot_alert(alert))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list Dependabot alerts: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list Dependabot alerts: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_dependabot_alerts handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_dependabot_alerts",
        description=translator("TOOL_LIST_DEPENDABOT_ALERTS_DESCRIPTION", "List Dependabot security alerts for a repository"),
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
                    "description": "Alert state filter",
                    "enum": ["open", "closed", "dismissed"]
                },
                "severity": {
                    "type": "string",
                    "description": "Severity level filter",
                    "enum": ["low", "medium", "high", "critical"]
                },
                "ecosystem": {
                    "type": "string",
                    "description": "Package ecosystem filter",
                    "enum": ["composer", "go", "maven", "npm", "nuget", "pip", "rubygems", "rust"]
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


def get_code_scanning_alert_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_code_scanning_alert tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            alert_number, err = required_param(request, "alert_number", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get code scanning alert
                repository = client.get_repo(f"{owner}/{repo}")
                alert = repository.get_code_scanning_alert(alert_number)
                alert_dict = convert_to_code_scanning_alert(alert)
                return marshalled_text_result(alert_dict)

            except Exception as e:
                logger.error(f"Failed to get code scanning alert {alert_number}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get code scanning alert {alert_number}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_code_scanning_alert handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_code_scanning_alert",
        description=translator("TOOL_GET_CODE_SCANNING_ALERT_DESCRIPTION", "Get details for a code scanning alert"),
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
                "alert_number": {
                    "type": "integer",
                    "description": "Code scanning alert number"
                }
            },
            "required": ["owner", "repo", "alert_number"]
        }
    )

    return tool, handler


def list_code_scanning_alerts_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_code_scanning_alerts tool."""

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

            tool_name, err = optional_param(request, "tool_name", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get code scanning alerts
                repository = client.get_repo(f"{owner}/{repo}")
                alerts = repository.get_code_scanning_alerts()

                # Convert to list of alerts
                result = []
                for alert in alerts:
                    result.append(convert_to_code_scanning_alert(alert))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list code scanning alerts: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list code scanning alerts: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_code_scanning_alerts handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_code_scanning_alerts",
        description=translator("TOOL_LIST_CODE_SCANNING_ALERTS_DESCRIPTION", "List code scanning alerts for a repository"),
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
                    "description": "Alert state filter",
                    "enum": ["open", "closed", "dismissed"]
                },
                "tool_name": {
                    "type": "string",
                    "description": "Tool name filter"
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


# Export the main functions for tool registration
def get_security_tools(get_client: GetClientFn, translator: Optional[TranslationHelperFunc] = None) -> List[Tuple[Tool, Callable]]:
    """Get all security-related tools."""
    if translator is None:
        translator = lambda key, default: default

    tools = [
        get_dependabot_alert_tool(get_client, translator),
        list_dependabot_alerts_tool(get_client, translator),
        get_code_scanning_alert_tool(get_client, translator),
        list_code_scanning_alerts_tool(get_client, translator),
    ]

    return tools
