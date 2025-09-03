"""
GitHub MCP Tools - Toolset definitions and organization
Converted from github-mcp-server/pkg/github/tools.go
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple
from mcp import Tool
import logging

logger = logging.getLogger(__name__)

# Type definitions
GetClientFn = Callable[[Any], Any]  # Context -> GitHub REST Client
GetGQLClientFn = Callable[[Any], Any]  # Context -> GitHub GraphQL Client
TranslationHelperFunc = Callable[[str, str], str]

DEFAULT_TOOLS = ["all"]


class Toolset:
    """Represents a collection of related tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.read_tools: List[Tuple[Tool, Callable]] = []
        self.write_tools: List[Tuple[Tool, Callable]] = []
        self.resource_templates: List[Any] = []
        self.prompts: List[Any] = []
        self.enabled = False

    def add_read_tools(self, *tools_and_handlers: Tuple[Tool, Callable]) -> 'Toolset':
        """Add read-only tools to this toolset."""
        self.read_tools.extend(tools_and_handlers)
        return self

    def add_write_tools(self, *tools_and_handlers: Tuple[Tool, Callable]) -> 'Toolset':
        """Add write tools to this toolset."""
        self.write_tools.extend(tools_and_handlers)
        return self

    def add_resource_templates(self, *templates: Any) -> 'Toolset':
        """Add resource templates to this toolset."""
        self.resource_templates.extend(templates)
        return self

    def add_prompts(self, *prompts: Any) -> 'Toolset':
        """Add prompts to this toolset."""
        self.prompts.extend(prompts)
        return self


class ToolsetGroup:
    """Manages a group of toolsets."""

    def __init__(self, read_only: bool = False):
        self.read_only = read_only
        self.toolsets: Dict[str, Toolset] = {}

    def add_toolset(self, toolset: Toolset) -> None:
        """Add a toolset to this group."""
        self.toolsets[toolset.name] = toolset

    def enable_toolset(self, name: str) -> bool:
        """Enable a toolset by name."""
        if name in self.toolsets:
            self.toolsets[name].enabled = True
            return True
        return False

    def get_enabled_toolsets(self) -> List[Toolset]:
        """Get all enabled toolsets."""
        return [ts for ts in self.toolsets.values() if ts.enabled]


def default_toolset_group(
    read_only: bool,
    get_client: GetClientFn,
    get_gql_client: GetGQLClientFn,
    get_raw_client: Optional[Callable] = None,
    translator: Optional[TranslationHelperFunc] = None,
    content_window_size: int = 5000
) -> ToolsetGroup:
    """
    Create the default toolset group with all available GitHub tools.
    """
    if translator is None:
        translator = lambda key, default: default

    tsg = ToolsetGroup(read_only=read_only)

    # Import tool modules here when they exist
    from . import repositories, issues, pullrequests, actions, security, misc_tools

    repos = Toolset("repos", "GitHub Repository related tools")
    repos.enabled = True  # Enable by default

    # Add repository tools
    try:
        repo_tools = repositories.get_repository_tools(get_client, None, translator)
        for tool, handler in repo_tools:
            # Classify tools as read or write based on their names
            if tool.name in ['create_or_update_file', 'create_branch', 'push_files', 'delete_file']:
                repos.add_write_tools((tool, handler))
            else:
                repos.add_read_tools((tool, handler))
    except AttributeError:
        # repositories module might not have the function yet
        pass

    issues_toolset = Toolset("issues", "GitHub Issues related tools")
    issues_toolset.enabled = True

    # Add issue tools
    try:
        issue_tools = issues.get_issue_tools(get_client, get_gql_client, translator)
        for tool, handler in issue_tools:
            if tool.name in ['create_issue', 'update_issue', 'add_issue_comment', 'add_sub_issue', 'remove_sub_issue', 'reprioritize_sub_issue']:
                issues_toolset.add_write_tools((tool, handler))
            else:
                issues_toolset.add_read_tools((tool, handler))
    except AttributeError:
        # issues module might not have the function yet
        pass

    pull_requests = Toolset("pull_requests", "GitHub Pull Request related tools")
    pull_requests.enabled = True

    # Add pull request tools
    try:
        pr_tools = pullrequests.get_pull_request_tools(get_client, get_gql_client, translator)
        for tool, handler in pr_tools:
            if tool.name in ['create_pull_request', 'merge_pull_request', 'update_pull_request', 'create_and_submit_pull_request_review', 'create_pending_pull_request_review', 'add_comment_to_pending_review', 'submit_pending_pull_request_review']:
                pull_requests.add_write_tools((tool, handler))
            else:
                pull_requests.add_read_tools((tool, handler))
    except AttributeError:
        # pullrequests module might not have the function yet
        pass



    users = Toolset("users", "GitHub User related tools")
    users.enabled = True

    orgs = Toolset("orgs", "GitHub Organization related tools")
    orgs.enabled = True

    code_security = Toolset("code_security", "Code security related tools")
    code_security.enabled = True

    secret_protection = Toolset("secret_protection", "Secret protection related tools")
    secret_protection.enabled = True

    dependabot = Toolset("dependabot", "Dependabot tools")
    dependabot.enabled = True

    # Add security tools
    try:
        from . import security as security_module
        security_tools = security_module.get_security_tools(get_client, translator)

        # Distribute tools to appropriate toolsets
        for tool, handler in security_tools:
            if 'dependabot' in tool.name:
                dependabot.add_read_tools((tool, handler))
            elif 'code_scanning' in tool.name:
                code_security.add_read_tools((tool, handler))
            else:
                # Add to both toolsets if not specific
                code_security.add_read_tools((tool, handler))
                dependabot.add_read_tools((tool, handler))
    except (AttributeError, ImportError):
        # security module might not have the function yet
        pass

    notifications = Toolset("notifications", "GitHub Notifications related tools")
    notifications.enabled = True

    discussions = Toolset("discussions", "GitHub Discussions related tools")
    discussions.enabled = True

    actions = Toolset("actions", "GitHub Actions workflows and CI/CD operations")
    actions.enabled = True

    # Add actions tools
    try:
        from . import actions as actions_module
        action_tools = actions_module.get_actions_tools(get_client, translator)
        for tool, handler in action_tools:
            if tool.name in ['run_workflow', 'rerun_workflow_run', 'rerun_failed_jobs', 'cancel_workflow_run', 'delete_workflow_run_logs']:
                actions.add_write_tools((tool, handler))
            else:
                actions.add_read_tools((tool, handler))
    except (AttributeError, ImportError):
        # actions module might not have the function yet
        pass

    security_advisories = Toolset("security_advisories", "Security advisories related tools")
    security_advisories.enabled = True

    # Context tools are always enabled
    context_tools = Toolset("context", "Tools that provide context about the current user and GitHub context")
    context_tools.enabled = True

    gists = Toolset("gists", "GitHub Gist related tools")
    gists.enabled = True

    # Add miscellaneous tools after all toolsets are defined
    try:
        misc_tools_list = misc_tools.get_misc_tools(get_client, get_gql_client, translator)

        # Distribute tools to appropriate toolsets
        for tool, handler in misc_tools_list:
            if tool.name in ['list_notifications', 'get_notification_details']:
                notifications.add_read_tools((tool, handler))
            elif tool.name in ['list_gists']:
                gists.add_read_tools((tool, handler))
            elif tool.name in ['create_gist', 'update_gist']:
                gists.add_write_tools((tool, handler))
            elif tool.name in ['get_discussion', 'list_discussions', 'get_discussion_comments', 'list_discussion_categories']:
                discussions.add_read_tools((tool, handler))
            elif tool.name in ['dismiss_notification', 'mark_all_notifications_read', 'manage_notification_subscription', 'manage_repository_notification_subscription']:
                notifications.add_write_tools((tool, handler))
            else:
                # Add to notifications by default for other notification-related tools
                notifications.add_read_tools((tool, handler))
    except (AttributeError, ImportError):
        # misc_tools module might not have the function yet
        pass

    # Experiments toolset (placeholder)
    experiments = Toolset("experiments", "Experimental features")
    experiments.enabled = False

    # Add all toolsets to the group
    tsg.add_toolset(context_tools)
    tsg.add_toolset(repos)
    tsg.add_toolset(issues_toolset)
    tsg.add_toolset(orgs)
    tsg.add_toolset(users)
    tsg.add_toolset(pull_requests)
    tsg.add_toolset(actions)
    tsg.add_toolset(code_security)
    tsg.add_toolset(secret_protection)
    tsg.add_toolset(dependabot)
    tsg.add_toolset(notifications)
    tsg.add_toolset(experiments)
    tsg.add_toolset(discussions)
    tsg.add_toolset(gists)
    tsg.add_toolset(security_advisories)

    return tsg


def init_dynamic_toolset(
    server: Any,
    tsg: ToolsetGroup,
    translator: Optional[TranslationHelperFunc] = None
) -> Toolset:
    """
    Create a dynamic toolset for enabling other toolsets.
    """
    if translator is None:
        translator = lambda key, default: default

    dynamic_toolset = Toolset(
        "dynamic",
        "Discover GitHub MCP tools that can help achieve tasks by enabling additional sets of tools"
    )

    # Dynamic toolset is always enabled
    dynamic_toolset.enabled = True

    return dynamic_toolset
