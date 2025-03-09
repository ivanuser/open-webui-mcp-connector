""" 
title: MCP Server Manager
author: Open WebUI Contributor
description: Manage MCP (Model Context Protocol) servers in Open WebUI
required_open_webui_version: 0.5.0
version: 0.1.0
license: MIT
"""

from pydantic import BaseModel, Field
from fastapi import Request
import json
import os
import uuid
from typing import Dict, List, Optional
import aiohttp

# Store for MCP server configurations
MCP_SERVERS_FILE = os.path.expanduser("~/.open-webui/mcp-servers.json")
os.makedirs(os.path.dirname(MCP_SERVERS_FILE), exist_ok=True)

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
    def __init__(self):
        self.valves = self.Valves()
        self.servers = load_mcp_servers()

    class Valves(BaseModel):
        pass

    async def list_servers(self, _user_: dict = None, _request_: Request = None) -> str:
        """List all configured MCP servers"""
        if not self.servers:
            return "No MCP servers configured. Use 'add_server' to add one."
        
        response = "## Configured MCP Servers\n\n"
        for server_id, server in self.servers.items():
            response += f"### {server.get('name', 'Unnamed Server')}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server.get('url', 'Not set')}\n"
            response += f"- Default Model: {server.get('default_model', 'Not set')}\n"
            response += f"- API Key: {'Configured' if server.get('api_key') else 'Not set'}\n\n"
        
        return response

    async def add_server(
        self, 
        name: str, 
        url: str, 
        api_key: str = "", 
        default_model: str = "",
        _user_: dict = None, 
        _request_: Request = None
    ) -> str:
        """
        Add a new MCP server
        :param name: Friendly name for the server
        :param url: Server URL (e.g., https://example.com/api)
        :param api_key: API key for authentication (optional)
        :param default_model: Default model to use for this server (optional)
        """
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

    async def update_server(
        self, 
        server_id: str, 
        name: str = None, 
        url: str = None, 
        api_key: str = None, 
        default_model: str = None,
        _user_: dict = None, 
        _request_: Request = None
    ) -> str:
        """
        Update an existing MCP server
        :param server_id: ID of the server to update
        :param name: New friendly name (optional)
        :param url: New server URL (optional)
        :param api_key: New API key (optional)
        :param default_model: New default model (optional)
        """
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

    async def delete_server(self, server_id: str, _user_: dict = None, _request_: Request = None) -> str:
        """
        Delete an MCP server
        :param server_id: ID of the server to delete
        """
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server_name = self.servers[server_id].get("name", "Unnamed Server")
        
        # Remove the server
        del self.servers[server_id]
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{server_name}' deleted successfully!"

    async def test_connection(self, server_id: str, _user_: dict = None, _request_: Request = None) -> str:
        """
        Test connection to an MCP server
        :param server_id: ID of the server to test
        """
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

    async def get_models(self, server_id: str, _user_: dict = None, _request_: Request = None) -> str:
        """
        Get available models from an MCP server
        :param server_id: ID of the server to query
        """
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