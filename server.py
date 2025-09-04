import os
import sys
import argparse
import logging
from mcp.server.fastmcp import FastMCP
from github_mcp.server import GitHubMCPServer
from github_mcp.clients import GitHubClientConfig, get_rest_client_factory, get_graphql_client_factory
from github_mcp.tools import default_toolset_group

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_server(args):
    """Create the GitHub MCP server with the given configuration."""

    # Get GitHub token from environment or args
    token = args.token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        logger.error("GitHub token is required. Set GITHUB_PERSONAL_ACCESS_TOKEN environment variable or use --token")
        sys.exit(1)

    # Create GitHub client configuration
    client_config = GitHubClientConfig(
        token=token,
        host=args.host,
        version="1.0.0"
    )

    # Create client factories
    get_client = get_rest_client_factory(client_config)
    get_gql_client = get_graphql_client_factory(client_config)

    # Create toolset group
    toolset_group = default_toolset_group(
        read_only=args.read_only,
        get_client=get_client,
        get_gql_client=get_gql_client
    )

    # Enable specified toolsets or all by default
    if args.toolsets and args.toolsets != ["all"]:
        # First disable all toolsets
        for toolset in toolset_group.toolsets.values():
            toolset.enabled = False

        # Enable only specified toolsets
        for toolset_name in args.toolsets:
            if toolset_name == "all":
                # Enable all toolsets
                for toolset in toolset_group.toolsets.values():
                    toolset.enabled = True
                logger.info("Enabled all toolsets (explicit 'all' specified)")
                break
            elif toolset_name in toolset_group.toolsets:
                toolset_group.toolsets[toolset_name].enabled = True
                logger.info(f"Enabled toolset: {toolset_name}")
            else:
                logger.warning(f"Toolset '{toolset_name}' not found")
    else:
        # Enable all toolsets by default (this is the default behavior)
        logger.info("Enabled all toolsets by default")

    # Create FastMCP server
    mcp = FastMCP(name="github-mcp-server")

    # Register tools from enabled toolsets
    tool_count = 0
    for toolset in toolset_group.get_enabled_toolsets():
        logger.info(f"Registering tools from toolset: {toolset.name}")

        # Register read tools
        for tool_obj, handler in toolset.read_tools:
            logger.info(f"Registering read tool: {tool_obj.name}")
            try:
                # FastMCP expects the handler function, not the Tool object
                # Use the tool metadata from the Tool object
                mcp.add_tool(
                    handler,
                    name=tool_obj.name,
                    description=tool_obj.description
                )
                tool_count += 1
            except Exception as e:
                logger.error(f"Failed to register tool {tool_obj.name}: {e}")

        # Register write tools if not in read-only mode
        if not toolset_group.read_only:
            for tool_obj, handler in toolset.write_tools:
                logger.info(f"Registering write tool: {tool_obj.name}")
                try:
                    mcp.add_tool(
                        handler,
                        name=tool_obj.name,
                        description=tool_obj.description
                    )
                    tool_count += 1
                except Exception as e:
                    logger.error(f"Failed to register tool {tool_obj.name}: {e}")

    logger.info(f"Successfully registered {tool_count} tools total")

    logger.info("GitHub MCP server initialized successfully")
    return mcp

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="GitHub MCP Server")
    parser.add_argument("--token", help="GitHub Personal Access Token")
    parser.add_argument("--host", default="github.com", help="GitHub hostname (default: github.com)")
    parser.add_argument("--read-only", action="store_true", help="Restrict to read-only operations")
    parser.add_argument("--toolsets", nargs="*", help="List of toolsets to enable")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        mcp = create_server(args)
        if mcp:
            # Start the server with stdio transport (matching Go version)
            mcp.run(transport="streamable-http")
        else:
            logger.error("Failed to initialize MCP server")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
