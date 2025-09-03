#!/usr/bin/env python3
"""
Test script for GitHub MCP server configurations
"""

from server import create_server

def test_server_configs():
    """Test various server configurations"""

    test_cases = [
        {'name': 'All toolsets', 'toolsets': None, 'read_only': False},
        {'name': 'Specific toolsets', 'toolsets': ['repos', 'issues'], 'read_only': False},
        {'name': 'Read-only mode', 'toolsets': None, 'read_only': True},
        {'name': 'All explicit', 'toolsets': ['all'], 'read_only': False},
    ]

    for test_case in test_cases:
        print(f"\n=== Testing: {test_case['name']} ===")

        class MockArgs:
            def __init__(self, toolsets, read_only):
                self.token = 'fake_token'
                self.host = 'github.com'
                self.toolsets = toolsets
                self.read_only = read_only
                self.log_level = 'ERROR'  # Reduce log noise

        args = MockArgs(test_case['toolsets'], test_case['read_only'])
        try:
            mcp = create_server(args)
            print(f'✅ {test_case["name"]}: Success')
        except Exception as e:
            print(f'❌ {test_case["name"]}: Error - {e}')

if __name__ == "__main__":
    test_server_configs()