"""
title: MCP Connector
author: Open WebUI Contributor
description: Connect to MCP (Model Context Protocol) servers from Open WebUI
required_open_webui_version: 0.5.0
version: 0.2.0
license: MIT
"""

from pydantic import BaseModel, Field
from fastapi import Request
import aiohttp
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

class Pipe:
    def __init__(self):
        self.valves = self.Valves()
        self.servers = load_mcp_servers()

    class Valves(BaseModel):
        server_id: str = Field("", description="ID of the MCP server to use (set up via server management commands)")
        default_model: str = Field("", description="Default model to use if not specified in the request")
        timeout_seconds: int = Field(30, description="Timeout for MCP server requests (in seconds)")
        stream: bool = Field(False, description="Enable streaming responses (if supported by server)")

    async def pipe(self, body: dict, _user_: dict = None, _request_: Request = None, _event_emitter_: Optional[callable] = None) -> str:
        """
        Process chat messages through an MCP server or handle server management commands
        """
        # Check if this is a special command
        messages = body.get("messages", [])
        if messages and len(messages) > 0 and "content" in messages[-1]:
            user_message = messages[-1]["content"].strip()
            
            # Handle server management commands
            if user_message.startswith("!mcp "):
                return await self._handle_command(user_message[5:], _event_emitter_)
            
            # Handle help command
            if user_message.strip() == "!mcp" or user_message.strip() == "!mcp help":
                return await self._show_help()

        # Regular MCP functionality
        # Reload server configurations to ensure we have the latest
        self.servers = load_mcp_servers()
        
        # Check if the server exists
        if not self.valves.server_id or self.valves.server_id not in self.servers:
            help_text = "Error: No MCP server selected. Please configure a server with MCP commands.\n\n"
            help_text += "To display a list of popular servers: `!mcp list_popular`\n"
            help_text += "To add a popular server: `!mcp add_popular brave_search your-api-key`\n"
            help_text += "To see all available commands: `!mcp help`"
            return help_text

        server_config = self.servers[self.valves.server_id]
        server_url = server_config.get("url", "")
        api_key = server_config.get("api_key", "")
        
        # Extract messages
        messages = body.get("messages", [])
        
        # Configure MCP request
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Get the model to use
        model = body.get("model", self.valves.default_model)
        if not model:
            model = server_config.get("default_model", "")
            
        # Prepare request payload for MCP server
        mcp_payload = {
            "messages": messages,
            "model": model,
            # Add other compatible parameters
            "temperature": body.get("temperature", 0.7),
            "max_tokens": body.get("max_tokens", 1000),
            "stream": self.valves.stream
        }
        
        # Emit status if event emitter is available
        if _event_emitter_:
            await _event_emitter_(
                {
                    "type": "status",
                    "data": {
                        "description": f"Connecting to MCP server: {server_config.get('name', server_url)}",
                        "done": False,
                        "hidden": False
                    },
                }
            )

        # Send request to MCP server
        try:
            async with aiohttp.ClientSession() as session:
                if self.valves.stream:
                    # Streaming implementation
                    return await self._handle_streaming(
                        session, server_url, headers, mcp_payload, 
                        _event_emitter_
                    )
                else:
                    # Non-streaming implementation
                    return await self._handle_non_streaming(
                        session, server_url, headers, mcp_payload, 
                        _event_emitter_
                    )
        except Exception as e:
            return f"Error: Failed to communicate with the MCP server: {str(e)}"

    async def _handle_command(self, command: str, _event_emitter_: Optional[callable] = None) -> str:
        """Handle MCP management commands"""
        parts = command.strip().split()
        if not parts:
            return "Invalid command. Use '!mcp help' to see available commands."
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Process commands
        if cmd == "list":
            return await self._list_servers()
        elif cmd == "list_popular" or cmd == "popular":
            return await self._list_popular_servers()
        elif cmd == "add":
            if len(args) < 2:
                return "Error: Missing arguments. Usage: !mcp add <name> <url> [api_key] [default_model]"
            name = args[0]
            url = args[1]
            api_key = args[2] if len(args) > 2 else ""
            default_model = args[3] if len(args) > 3 else ""
            return await self._add_server(name, url, api_key, default_model)
        elif cmd == "add_popular":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: !mcp add_popular <server_id> [api_key] [default_model]"
            server_id = args[0]
            api_key = args[1] if len(args) > 1 else ""
            default_model = args[2] if len(args) > 2 else ""
            return await self._add_popular_server(server_id, api_key, default_model)
        elif cmd == "update":
            if len(args) < 2:
                return "Error: Missing arguments. Usage: !mcp update <server_id> <field> <value>"
            server_id = args[0]
            field = args[1].lower()
            value = args[2] if len(args) > 2 else ""
            return await self._update_server(server_id, field, value)
        elif cmd == "delete" or cmd == "remove":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: !mcp delete <server_id>"
            server_id = args[0]
            return await self._delete_server(server_id)
        elif cmd == "test":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: !mcp test <server_id>"
            server_id = args[0]
            return await self._test_connection(server_id)
        elif cmd == "models":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: !mcp models <server_id>"
            server_id = args[0]
            return await self._get_models(server_id)
        elif cmd == "use":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: !mcp use <server_id>"
            server_id = args[0]
            return await self._use_server(server_id)
        elif cmd == "help" or cmd == "":
            return await self._show_help()
        else:
            return f"Unknown command: {cmd}. Use '!mcp help' to see available commands."

    async def _show_help(self) -> str:
        """Show help for MCP commands"""
        help_text = "# MCP Connector Commands\n\n"
        help_text += "Use these commands to manage your MCP servers:\n\n"
        help_text += "- `!mcp list` - List all configured MCP servers\n"
        help_text += "- `!mcp list_popular` - List predefined popular MCP servers\n"
        help_text += "- `!mcp add <name> <url> [api_key] [default_model]` - Add a new MCP server\n"
        help_text += "- `!mcp add_popular <server_id> [api_key] [default_model]` - Add a predefined popular server\n"
        help_text += "- `!mcp update <server_id> <field> <value>` - Update a server (fields: name, url, api_key, default_model)\n"
        help_text += "- `!mcp delete <server_id>` - Delete a server\n"
        help_text += "- `!mcp test <server_id>` - Test connection to a server\n"
        help_text += "- `!mcp models <server_id>` - Get available models from a server\n"
        help_text += "- `!mcp use <server_id>` - Select a server to use for this session\n"
        help_text += "- `!mcp help` - Show this help message\n\n"
        help_text += "Example usage:\n"
        help_text += "```\n!mcp list_popular\n!mcp add_popular brave_search your-api-key\n!mcp use server-id-from-list\n```"
        return help_text

    async def _list_servers(self) -> str:
        """List all configured MCP servers"""
        # Reload server configurations to ensure we have the latest
        self.servers = load_mcp_servers()
        
        if not self.servers:
            return "No MCP servers configured. Use '!mcp add' to add one, or '!mcp list_popular' to see predefined options."
        
        response = "## Configured MCP Servers\n\n"
        for server_id, server in self.servers.items():
            response += f"### {server.get('name', 'Unnamed Server')}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server.get('url', 'Not set')}\n"
            response += f"- Default Model: {server.get('default_model', 'Not set')}\n"
            response += f"- API Key: {'Configured' if server.get('api_key') else 'Not set'}\n\n"
        
        return response

    async def _list_popular_servers(self) -> str:
        """List popular predefined MCP servers that can be easily added"""
        response = "## Popular MCP Servers\n\n"
        response += "These are popular MCP servers that you can add to your configuration. Use the '!mcp add_popular' command with the server ID.\n\n"
        
        for server_id, server in POPULAR_SERVERS.items():
            response += f"### {server['name']}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server['url']}\n"
            response += f"- Description: {server['description']}\n"
            response += f"- API Key Required: {'Yes' if server['needs_api_key'] else 'No'}\n\n"
        
        response += "To add one of these servers, use the command:\n"
        response += "```\n!mcp add_popular server_id api_key default_model\n```\n"
        response += "For example:\n"
        response += "```\n!mcp add_popular brave_search your-api-key\n```\n"
        
        return response

    async def _add_popular_server(self, server_id: str, api_key: str = "", default_model: str = "") -> str:
        """Add a predefined popular MCP server"""
        # Reload server configurations to ensure we have the latest
        self.servers = load_mcp_servers()
        
        if server_id not in POPULAR_SERVERS:
            return f"Error: No predefined server found with ID '{server_id}'. Use '!mcp list_popular' to see available options."
        
        server_info = POPULAR_SERVERS[server_id]
        
        # Check if API key is needed but not provided
        if server_info["needs_api_key"] and not api_key:
            return f"Error: The server '{server_info['name']}' requires an API key. Please provide one using: !mcp add_popular {server_id} your-api-key"
        
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
        
        return f"MCP server '{server_info['name']}' added successfully!\nServer ID: `{new_server_id}`\n\nUse this ID to configure this session with: !mcp use {new_server_id}"

    async def _add_server(self, name: str, url: str, api_key: str = "", default_model: str = "") -> str:
        """Add a new MCP server"""
        # Reload server configurations to ensure we have the latest
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
        
        return f"MCP server '{name}' added successfully!\nServer ID: `{server_id}`\n\nUse this ID to configure this session with: !mcp use {server_id}"

    async def _update_server(self, server_id: str, field: str, value: str) -> str:
        """Update an existing MCP server"""
        # Reload server configurations to ensure we have the latest
        self.servers = load_mcp_servers()
        
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server = self.servers[server_id]
        
        # Update the specified field
        if field == "name":
            server["name"] = value
        elif field == "url":
            # Validate URL
            if not value.startswith(("http://", "https://")):
                return "Error: URL must start with http:// or https://"
            server["url"] = value
        elif field == "api_key":
            server["api_key"] = value
        elif field == "default_model":
            server["default_model"] = value
        else:
            return f"Error: Unknown field '{field}'. Valid fields are: name, url, api_key, default_model"
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{server['name']}' updated successfully!"

    async def _delete_server(self, server_id: str) -> str:
        """Delete an MCP server"""
        # Reload server configurations to ensure we have the latest
        self.servers = load_mcp_servers()
        
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server_name = self.servers[server_id].get("name", "Unnamed Server")
        
        # Remove the server
        del self.servers[server_id]
        
        # Save the updated configuration
        save_mcp_servers(self.servers)
        
        return f"MCP server '{server_name}' deleted successfully!"

    async def _test_connection(self, server_id: str) -> str:
        """Test connection to an MCP server"""
        # Reload server configurations to ensure we have the latest
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

    async def _get_models(self, server_id: str) -> str:
        """Get available models from an MCP server"""
        # Reload server configurations to ensure we have the latest
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

    async def _use_server(self, server_id: str) -> str:
        """Select a server to use for this session"""
        # Reload server configurations to ensure we have the latest
        self.servers = load_mcp_servers()
        
        if server_id not in self.servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server = self.servers[server_id]
        
        # Update the valve
        self.valves.server_id = server_id
        
        return f"Now using MCP server '{server.get('name')}' for this session.\n\nYou can now chat with this server!"

    async def _handle_non_streaming(self, session, server_url, headers, payload, _event_emitter_):
        """Handle non-streaming request to MCP server"""
        async with session.post(
            f"{server_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return f"Error connecting to MCP server: {response.status} - {error_text}"
            
            response_json = await response.json()
            
            # Extract the response content
            if "choices" in response_json and len(response_json["choices"]) > 0:
                content = response_json["choices"][0].get("message", {}).get("content", "")
                
                # Emit completion status if event emitter is available
                if _event_emitter_:
                    await _event_emitter_(
                        {
                            "type": "status",
                            "data": {
                                "description": "Response received from MCP server",
                                "done": True,
                                "hidden": False
                            },
                        }
                    )
                
                return content
            else:
                return "No content received from MCP server"

    async def _handle_streaming(self, session, server_url, headers, payload, _event_emitter_):
        """Handle streaming request to MCP server"""
        full_response = ""
        
        async with session.post(
            f"{server_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return f"Error connecting to MCP server: {response.status} - {error_text}"
            
            # Process the streaming response
            async for line in response.content:
                line = line.decode('utf-8').strip()
                
                # Skip empty lines and [DONE] marker
                if not line or line == "data: [DONE]":
                    continue
                
                # Remove "data: " prefix if present
                if line.startswith("data: "):
                    line = line[6:]
                
                try:
                    chunk = json.loads(line)
                    
                    # Extract content delta
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            content_chunk = delta["content"]
                            full_response += content_chunk
                except:
                    # Skip lines that can't be parsed as JSON
                    continue
        
        # Emit completion status if event emitter is available
        if _event_emitter_:
            await _event_emitter_(
                {
                    "type": "status",
                    "data": {
                        "description": "Response received from MCP server",
                        "done": True,
                        "hidden": False
                    },
                }
            )
        
        return full_response