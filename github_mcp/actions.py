"""
GitHub Actions Tools
Converted from github-mcp-server/pkg/github/actions.go
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
from .clients import GraphQLClient
import logging

logger = logging.getLogger(__name__)

# Type definitions for GitHub API responses
def convert_to_workflow(workflow: Any) -> Dict[str, Any]:
    """Convert GitHub workflow to dictionary format."""
    if not workflow:
        return {}

    return {
        'id': getattr(workflow, 'id', 0),
        'name': getattr(workflow, 'name', ''),
        'path': getattr(workflow, 'path', ''),
        'state': getattr(workflow, 'state', ''),
        'created_at': getattr(workflow, 'created_at', '').isoformat() if hasattr(workflow, 'created_at') and workflow.created_at else None,
        'updated_at': getattr(workflow, 'updated_at', '').isoformat() if hasattr(workflow, 'updated_at') and workflow.updated_at else None,
        'html_url': getattr(workflow, 'html_url', ''),
    }


def convert_to_workflow_run(run: Any) -> Dict[str, Any]:
    """Convert GitHub workflow run to dictionary format."""
    if not run:
        return {}

    result = {
        'id': getattr(run, 'id', 0),
        'name': getattr(run, 'name', ''),
        'head_branch': getattr(run, 'head_branch', ''),
        'head_sha': getattr(run, 'head_sha', ''),
        'run_number': getattr(run, 'run_number', 0),
        'event': getattr(run, 'event', ''),
        'status': getattr(run, 'status', ''),
        'conclusion': getattr(run, 'conclusion', ''),
        'created_at': getattr(run, 'created_at', '').isoformat() if hasattr(run, 'created_at') and run.created_at else None,
        'updated_at': getattr(run, 'updated_at', '').isoformat() if hasattr(run, 'updated_at') and run.updated_at else None,
        'html_url': getattr(run, 'html_url', ''),
    }

    # Extract trigger actor information
    if hasattr(run, 'triggering_actor') and run.triggering_actor:
        result['triggering_actor'] = {
            'login': getattr(run.triggering_actor, 'login', ''),
            'id': getattr(run.triggering_actor, 'id', 0),
            'html_url': getattr(run.triggering_actor, 'html_url', ''),
        }

    return result


def convert_to_workflow_job(job: Any) -> Dict[str, Any]:
    """Convert GitHub workflow job to dictionary format."""
    if not job:
        return {}

    result = {
        'id': getattr(job, 'id', 0),
        'run_id': getattr(job, 'run_id', 0),
        'name': getattr(job, 'name', ''),
        'status': getattr(job, 'status', ''),
        'conclusion': getattr(job, 'conclusion', ''),
        'started_at': getattr(job, 'started_at', '').isoformat() if hasattr(job, 'started_at') and job.started_at else None,
        'completed_at': getattr(job, 'completed_at', '').isoformat() if hasattr(job, 'completed_at') and job.completed_at else None,
        'html_url': getattr(job, 'html_url', ''),
    }

    # Extract steps information
    if hasattr(job, 'steps'):
        result['steps'] = []
        for step in job.steps or []:
            result['steps'].append({
                'name': getattr(step, 'name', ''),
                'status': getattr(step, 'status', ''),
                'conclusion': getattr(step, 'conclusion', ''),
                'number': getattr(step, 'number', 0),
                'started_at': getattr(step, 'started_at', '').isoformat() if hasattr(step, 'started_at') and step.started_at else None,
                'completed_at': getattr(step, 'completed_at', '').isoformat() if hasattr(step, 'completed_at') and step.completed_at else None,
            })

    return result


def convert_to_artifact(artifact: Any) -> Dict[str, Any]:
    """Convert GitHub artifact to dictionary format."""
    if not artifact:
        return {}

    return {
        'id': getattr(artifact, 'id', 0),
        'name': getattr(artifact, 'name', ''),
        'size_in_bytes': getattr(artifact, 'size_in_bytes', 0),
        'created_at': getattr(artifact, 'created_at', '').isoformat() if hasattr(artifact, 'created_at') and artifact.created_at else None,
        'expired': getattr(artifact, 'expired', False),
        'expires_at': getattr(artifact, 'expires_at', '').isoformat() if hasattr(artifact, 'expires_at') and artifact.expires_at else None,
    }


def list_workflows_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_workflows tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get workflows
                repository = client.get_repo(f"{owner}/{repo}")
                workflows = repository.get_workflows()

                # Convert to list of workflows
                result = []
                for workflow in workflows:
                    result.append(convert_to_workflow(workflow))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list workflows: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list workflows: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_workflows handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_workflows",
        description=translator("TOOL_LIST_WORKFLOWS_DESCRIPTION", "List GitHub Actions workflows for a repository"),
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


def list_workflow_runs_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_workflow_runs tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            workflow_id, err = optional_param(request, "workflow_id", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            branch, err = optional_param(request, "branch", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            event, err = optional_param(request, "event", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            status, err = optional_param(request, "status", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get workflow runs
                repository = client.get_repo(f"{owner}/{repo}")

                if workflow_id:
                    # Get runs for specific workflow
                    workflow = repository.get_workflow(workflow_id)
                    runs = workflow.get_runs()
                else:
                    # Get all runs for repository
                    runs = repository.get_workflow_runs()

                # Apply filters if provided
                filtered_runs = []
                for run in runs:
                    if branch and getattr(run, 'head_branch', '') != branch:
                        continue
                    if event and getattr(run, 'event', '') != event:
                        continue
                    if status and getattr(run, 'status', '') != status:
                        continue
                    filtered_runs.append(run)

                # Convert to list of runs
                result = []
                for run in filtered_runs[:pagination.per_page]:
                    result.append(convert_to_workflow_run(run))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list workflow runs: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list workflow runs: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_workflow_runs handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_workflow_runs",
        description=translator("TOOL_LIST_WORKFLOW_RUNS_DESCRIPTION", "List GitHub Actions workflow runs for a repository"),
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
                "workflow_id": {
                    "type": "string",
                    "description": "Workflow ID or filename to filter by"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name to filter runs by"
                },
                "event": {
                    "type": "string",
                    "description": "Event type to filter runs by"
                },
                "status": {
                    "type": "string",
                    "description": "Run status to filter by",
                    "enum": ["completed", "in_progress", "queued"]
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


def get_workflow_run_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the get_workflow_run tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            run_id, err = required_param(request, "run_id", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get workflow run
                repository = client.get_repo(f"{owner}/{repo}")
                run = repository.get_workflow_run(run_id)
                run_dict = convert_to_workflow_run(run)
                return marshalled_text_result(run_dict)

            except Exception as e:
                logger.error(f"Failed to get workflow run {run_id}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to get workflow run {run_id}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in get_workflow_run handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="get_workflow_run",
        description=translator("TOOL_GET_WORKFLOW_RUN_DESCRIPTION", "Get details for a GitHub Actions workflow run"),
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
                "run_id": {
                    "type": "integer",
                    "description": "Workflow run ID"
                }
            },
            "required": ["owner", "repo", "run_id"]
        }
    )

    return tool, handler


def run_workflow_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the run_workflow tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            workflow_id, err = required_param(request, "workflow_id", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            ref, err = required_param(request, "ref", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            inputs, err = optional_param(request, "inputs", dict)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Run workflow
                repository = client.get_repo(f"{owner}/{repo}")
                workflow = repository.get_workflow(workflow_id)

                # Prepare dispatch parameters
                dispatch_params = {
                    'ref': ref,
                }

                if inputs:
                    dispatch_params['inputs'] = inputs

                result = workflow.create_dispatch(**dispatch_params)

                return marshalled_text_result({
                    'message': 'Workflow dispatched successfully',
                    'workflow_id': workflow_id,
                    'ref': ref
                })

            except Exception as e:
                logger.error(f"Failed to run workflow {workflow_id}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to run workflow {workflow_id}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in run_workflow handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="run_workflow",
        description=translator("TOOL_RUN_WORKFLOW_DESCRIPTION", "Trigger a GitHub Actions workflow run"),
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
                "workflow_id": {
                    "type": "string",
                    "description": "Workflow ID or filename"
                },
                "ref": {
                    "type": "string",
                    "description": "Git reference (branch, tag, or SHA) to run the workflow on"
                },
                "inputs": {
                    "type": "object",
                    "description": "Input parameters for the workflow",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["owner", "repo", "workflow_id", "ref"]
        }
    )

    return tool, handler


def list_workflow_run_artifacts_tool(get_client: GetClientFn, translator: TranslationHelperFunc) -> Tuple[Tool, Callable]:
    """Create the list_workflow_run_artifacts tool."""

    def handler(ctx: Any, request: CallToolRequest) -> CallToolResult:
        try:
            # Extract parameters
            owner, err = required_param(request, "owner", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            repo, err = required_param(request, "repo", str)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            run_id, err = required_param(request, "run_id", int)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            pagination, err = optional_pagination_params(request)
            if err:
                return CallToolResult(type="error", error={"message": str(err)})

            # Get GitHub client
            client = get_client(ctx)

            try:
                # Get workflow run artifacts
                repository = client.get_repo(f"{owner}/{repo}")
                run = repository.get_workflow_run(run_id)
                artifacts = run.get_artifacts()

                # Convert to list of artifacts
                result = []
                for artifact in artifacts:
                    result.append(convert_to_artifact(artifact))

                return marshalled_text_result(result)

            except Exception as e:
                logger.error(f"Failed to list workflow run artifacts for {run_id}: {e}")
                return CallToolResult(type="error", error={"message": f"Failed to list workflow run artifacts for {run_id}: {str(e)}"})

        except Exception as e:
            logger.error(f"Error in list_workflow_run_artifacts handler: {e}")
            return CallToolResult(type="error", error={"message": str(e)})

    tool = Tool(
        name="list_workflow_run_artifacts",
        description=translator("TOOL_LIST_WORKFLOW_RUN_ARTIFACTS_DESCRIPTION", "List artifacts for a GitHub Actions workflow run"),
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
                "run_id": {
                    "type": "integer",
                    "description": "Workflow run ID"
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
            "required": ["owner", "repo", "run_id"]
        }
    )

    return tool, handler


# Export the main functions for tool registration
def get_actions_tools(get_client: GetClientFn, translator: Optional[TranslationHelperFunc] = None) -> List[Tuple[Tool, Callable]]:
    """Get all GitHub Actions-related tools."""
    if translator is None:
        translator = lambda key, default: default

    tools = [
        list_workflows_tool(get_client, translator),
        list_workflow_runs_tool(get_client, translator),
        get_workflow_run_tool(get_client, translator),
        list_workflow_run_artifacts_tool(get_client, translator),
    ]

    # Add write tools (these require write permissions)
    write_tools = [
        run_workflow_tool(get_client, translator),
    ]

    tools.extend(write_tools)

    return tools
