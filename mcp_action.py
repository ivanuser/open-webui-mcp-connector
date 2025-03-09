"""
title: MCP Server Manager
author: Open WebUI Contributor
description: Manage MCP (Model Context Protocol) servers in Open WebUI
required_open_webui_version: 0.5.0
version: 0.1.1
license: MIT
"""

from pydantic import BaseModel, Field
from fastapi import Request
import json
import os
import uuid
from typing import Dict, List, Optional, Literal
import aiohttp

# Store for MCP server configurations
MCP_SERVERS_FILE = os.path.expanduser("~/.open-webui/mcp-servers.json")
os.makedirs(os.path.dirname(MCP_SERVERS_FILE), exist_ok=True)

# Predefined list of popular MCP servers
POPULAR_SERVERS = {
    "anthropic_official": {
        "name": "Anthropic Reference Implementation",
        "url": "https://mcp.anthropic.com/v1/anthropic",
        "description": "Official Anthropic MCP server with core features",
        "needs_api_key": True
    },
    "brave_search": {
        "name": "Brave Search",
        "url": "https://mcp.brave.com/v1/search",
        "description": "Web and local search using Brave's Search API",
        "needs_api_key": True
    },
    "kagi_search": {
        "name": "Kagi Search",
        "url": "https://kagi.com/api/v1/mcp",
        "description": "Search the web using Kagi's search API",
        "needs_api_key": True
    },
    "tavily": {
        "name": "Tavily Search",
        "url": "https://api.tavily.com/mcp",
        "description": "Search engine for AI agents by Tavily",
        "needs_api_key": True
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1/mcp",
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
        self.servers = load_mcp_servers()

    async def list_servers(self) -> str:
        """List all configured MCP servers"""
        self.servers = load_mcp_servers()
        if not self.servers:
            return "No MCP servers configured. Use 'add_server' to add one, or 'list_popular_servers' to see predefined options."
        
        response = "## Configured MCP Servers\n\n"
        for server_id, server in self.servers.items():
            response += f"### {server.get('name', 'Unnamed Server')}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server.get('url', 'Not set')}\n"
            response += f"- Default Model: {server.get('default_model', 'Not set')}\n"
            response += f"- API Key: {'Configured' if server.get('api_key') else 'Not set'}\n\n"
        
        return response

    async def list_popular_servers(self) -> str:
        """List popular predefined MCP servers that can be easily added"""
        response = "## Popular MCP Servers\n\n"
        response += "These are popular MCP servers that you can add to your configuration. Use the 'add_popular_server' command with the server ID.\n\n"
        
        for server_id, server in POPULAR_SERVERS.items():
            response += f"### {server['name']}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server['url']}\n"
            response += f"- Description: {server['description']}\n"
            response += f"- API Key Required: {'Yes' if server['needs_api_key'] else 'No'}\n\n"
        
        response += "To add one of these servers, use the command:\n"
        response += "```\n/add_popular_server server_id=\"server_id\" api_key=\"your-api-key\" default_model=\"model-name\"\n```\n"
        
        return response

    async def add_popular_server(self, server_id: str, api_key: str = "", default_model: str = "") -> str:
        """
        Add a predefined popular MCP server
        :param server_id: ID of the predefined server (from the list_popular_servers command)
        :param api_key: API key for authentication (required for some servers)
        :param default_model: Default model to use for this server (optional)
        """
        self.servers = load_mcp_servers()
        if server_id not in POPULAR_SERVERS:
            return f"Error: No predefined server found with ID '{server_id}'. Use 'list_popular_servers' to see available options."
        
        server_info = POPULAR_SERVERS[server_id]
        
        # Check if API key is needed but not provided
        if server_info["needs_api_key"] and not api_key:
            return f"Error: The server '{server_info['name']}' requires an API key. Please provide one using the api_key parameter."
        
        # Generate a unique ID for the server
        new_server_id = str(uuid.uuid4())
        
        # Add the server to the configuration
        self.servers[new_server_id] = {
            "name": server_info["name"],
            "url": server_info["url"],
            "api_key": api_key,
            "default_model": default_model
        }
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{server_info['name']}' added successfully!\nServer ID: `{new_server_id}`\n\nUse this ID in the MCP Connector Pipe Function configuration."

    async def add_server(self, name: str, url: str, api_key: str = "", default_model: str = "") -> str:
        """
        Add a new MCP server
        :param name: Friendly name for the server
        :param url: Server URL (e.g., https://example.com/api)
        :param api_key: API key for authentication (optional)
        :param default_model: Default model to use for this server (optional)
        """
        self.servers = load_mcp_servers()
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return "Error: URL must start with http:// or https://"
        
        # Generate a unique ID for the server
        server_id = str(uuid.uuid4())
        
        # Add the server to the configuration
        self.servers[server_id] = {
            "name": name,
            "url": url,
            "api_key": api_key,
            "default_model": default_model
        }
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{name}' added successfully!\nServer ID: `{server_id}`\n\nUse this ID in the MCP Connector Pipe Function configuration."

    async def update_server(self, server_id: str, name: str = None, url: str = None, api_key: str = None, default_model: str = None) -> str:
        """
        Update an existing MCP server
        :param server_id: ID of the server to update
        :param name: New friendly name (optional)
        :param url: New server URL (optional)
        :param api_key: New API key (optional)
        :param default_model: New default model (optional)
        """
        self.servers = load_mcp_servers()
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server = self.servers[server_id]
        
        # Update only the provided values
        if name is not None:
            server["name"] = name
        if url is not None:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                return "Error: URL must start with http:// or https://"
            server["url"] = url
        if api_key is not None:
            server["api_key"] = api_key
        if default_model is not None:
            server["default_model"] = default_model
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{server['name']}' updated successfully!"

    async def delete_server(self, server_id: str) -> str:
        """
        Delete an MCP server
        :param server_id: ID of the server to delete
        """
        self.servers = load_mcp_servers()
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server_name = self.servers[server_id].get("name", "Unnamed Server")
        
        # Remove the server
        del self.servers[server_id]
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{server_name}' deleted successfully!"

    async def test_connection(self, server_id: str) -> str:
        """
        Test connection to an MCP server
        :param server_id: ID of the server to test
        """
        self.servers = load_mcp_servers()
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server = self.servers[server_id]
        server_url = server.get("url", "")
        api_key = server.get("api_key", "")
        
        # Configure request
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Test simple models endpoint (common in OpenAI-compatible APIs)
        test_url = f"{server_url}/v1/models"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Error connecting to MCP server: {response.status} - {error_text}"
                    
                    models_json = await response.json()
                    
                    # Format the response
                    response_text = f"## Connection to '{server.get('name', 'Unnamed Server')}' successful!\n\n"
                    response_text += "### Available Models:\n"
                    
                    if "data" in models_json and isinstance(models_json["data"], list):
                        for model in models_json["data"]:
                            model_id = model.get("id", "Unknown")
                            response_text += f"- {model_id}\n"
                    else:
                        response_text += "- Unable to retrieve model list\n"
                    
                    return response_text
        except Exception as e:
            return f"Error: Failed to communicate with the MCP server: {str(e)}"

    async def get_models(self, server_id: str) -> str:
        """
        Get available models from an MCP server
        :param server_id: ID of the server to query
        """
        self.servers = load_mcp_servers()
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server = self.servers[server_id]
        server_url = server.get("url", "")
        api_key = server.get("api_key", "")
        
        # Configure request
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Get models from the server
        models_url = f"{server_url}/v1/models"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    models_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Error getting models from MCP server: {response.status} - {error_text}"
                    
                    models_json = await response.json()
                    
                    # Format the response
                    response_text = f"## Models available on '{server.get('name', 'Unnamed Server')}':\n\n"
                    
                    if "data" in models_json and isinstance(models_json["data"], list):
                        for model in models_json["data"]:
                            model_id = model.get("id", "Unknown")
                            response_text += f"- `{model_id}`\n"
                            
                            # Add model details if available
                            if "owned_by" in model:
                                response_text += f"  - Owner: {model['owned_by']}\n"
                            if "created" in model:
                                response_text += f"  - Created: {model['created']}\n"
                    else:
                        response_text += "No models found or unexpected response format.\n"
                    
                    return response_text
        except Exception as e:
            return f"Error: Failed to get models from the MCP server: {str(e)}"