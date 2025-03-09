"""
title: MCP Server Manager
author: Open WebUI Contributor
description: Manage MCP (Model Context Protocol) servers in Open WebUI
required_open_webui_version: 0.5.0
version: 0.2.0
license: MIT
"""

import json
import os
import uuid
from typing import Dict, List, Optional

# Store for MCP server configurations
MCP_SERVERS_FILE = os.path.expanduser("~/.open-webui/mcp-servers.json")
os.makedirs(os.path.dirname(MCP_SERVERS_FILE), exist_ok=True)

# Predefined list of popular MCP servers
POPULAR_SERVERS = {
    "anthropic_official": {
        "name": "Anthropic Reference Implementation",
        "url": "https://mcp.anthropic.com/v1",
        "description": "Official Anthropic MCP server with core features",
        "needs_api_key": True
    },
    "brave_search": {
        "name": "Brave Search",
        "url": "https://mcp.brave.com/v1",
        "description": "Web and local search using Brave's Search API",
        "needs_api_key": True
    },
    "kagi_search": {
        "name": "Kagi Search",
        "url": "https://kagi.com/api/v1",
        "description": "Search the web using Kagi's search API",
        "needs_api_key": True
    },
    "tavily": {
        "name": "Tavily Search",
        "url": "https://api.tavily.com/v1",
        "description": "Search engine for AI agents by Tavily",
        "needs_api_key": True
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1",
        "description": "OpenAI models integration",
        "needs_api_key": True
    },
    "filesystem": {
        "name": "Filesystem",
        "url": "http://localhost:3000",
        "description": "Local filesystem access (requires local server setup)",
        "needs_api_key": False
    },
    "github": {
        "name": "GitHub",
        "url": "http://localhost:3001",
        "description": "GitHub API integration (requires local server setup)",
        "needs_api_key": True
    },
    "memory": {
        "name": "Memory",
        "url": "http://localhost:3002",
        "description": "Knowledge graph-based memory system (requires local server setup)",
        "needs_api_key": False
    }
}

def load_mcp_servers() -> Dict:
    """Load MCP server configurations from file"""
    if not os.path.exists(MCP_SERVERS_FILE):
        return {}
    try:
        with open(MCP_SERVERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_mcp_servers(servers: Dict) -> None:
    """Save MCP server configurations to file"""
    with open(MCP_SERVERS_FILE, "w") as f:
        json.dump(servers, f)

class Action:
    def init(self):
        """Initialize the Action function"""
        pass

    async def list_servers(self) -> str:
        """List all configured MCP servers"""
        servers = load_mcp_servers()
        
        if not servers:
            return "No MCP servers configured. Use 'add_server' to add one, or 'list_popular_servers' to see predefined options."
        
        response = "## Configured MCP Servers\n\n"
        for server_id, server in servers.items():
            response += f"### {server.get('name', 'Unnamed Server')}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server.get('url', 'Not set')}\n"
            response += f"- Default Model: {server.get('default_model', 'Not set')}\n"
            response += f"- API Key: {'Configured' if server.get('api_key') else 'Not set'}\n\n"
        
        response += "To use a server, go to Admin > Settings > Functions, click the gear icon on the MCP Connector, and enter the server ID in the configuration."
        
        return response

    async def list_popular_servers(self) -> str:
        """List popular predefined MCP servers that can be easily added"""
        response = "## Popular MCP Servers\n\n"
        response += "These are popular MCP servers that you can add to your configuration using the add_popular_server command.\n\n"
        
        for server_id, server in POPULAR_SERVERS.items():
            response += f"### {server['name']}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server['url']}\n"
            response += f"- Description: {server['description']}\n"
            response += f"- API Key Required: {'Yes' if server['needs_api_key'] else 'No'}\n\n"
        
        return response

    async def add_popular_server(self, server_id: str, api_key: str = "", default_model: str = "") -> str:
        """
        Add a predefined popular MCP server
        :param server_id: ID of the predefined server (from the list_popular_servers command)
        :param api_key: API key for authentication (required for some servers)
        :param default_model: Default model to use for this server (optional)
        """
        servers = load_mcp_servers()
        
        if server_id not in POPULAR_SERVERS:
            return f"Error: No predefined server found with ID '{server_id}'. Use 'list_popular_servers' to see available options."
        
        server_info = POPULAR_SERVERS[server_id]
        
        # Check if API key is needed but not provided
        if server_info["needs_api_key"] and not api_key:
            return f"Error: The server '{server_info['name']}' requires an API key. Please provide one using the api_key parameter."
        
        # Generate a unique ID for the server
        new_server_id = str(uuid.uuid4())
        
        # Add the server to the configuration
        servers[new_server_id] = {
            "name": server_info["name"],
            "url": server_info["url"],
            "api_key": api_key,
            "default_model": default_model
        }
        
        # Save the updated configuration
        save_mcp_servers(servers)
        
        return f"MCP server '{server_info['name']}' added successfully!\n\nServer ID: `{new_server_id}`\n\nTo use this server, go to Admin > Settings > Functions, click the gear icon on the MCP Connector, and enter this ID in the server_id field."

    async def add_server(self, name: str, url: str, api_key: str = "", default_model: str = "") -> str:
        """
        Add a new MCP server
        :param name: Friendly name for the server
        :param url: Server URL (e.g., https://example.com/api)
        :param api_key: API key for authentication (optional)
        :param default_model: Default model to use for this server (optional)
        """
        servers = load_mcp_servers()
        
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return "Error: URL must start with http:// or https://"
        
        # Generate a unique ID for the server
        server_id = str(uuid.uuid4())
        
        # Add the server to the configuration
        servers[server_id] = {
            "name": name,
            "url": url,
            "api_key": api_key,
            "default_model": default_model
        }
        
        # Save the updated configuration
        save_mcp_servers(servers)
        
        return f"MCP server '{name}' added successfully!\n\nServer ID: `{server_id}`\n\nTo use this server, go to Admin > Settings > Functions, click the gear icon on the MCP Connector, and enter this ID in the server_id field."

    async def delete_server(self, server_id: str) -> str:
        """
        Delete an MCP server
        :param server_id: ID of the server to delete
        """
        servers = load_mcp_servers()
        
        if server_id not in servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server_name = servers[server_id].get("name", "Unnamed Server")
        
        # Remove the server
        del servers[server_id]
        
        # Save the updated configuration
        save_mcp_servers(servers)
        
        return f"MCP server '{server_name}' deleted successfully!"