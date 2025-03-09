"""
title: MCP Connector
author: Open WebUI Contributor
description: Connect to MCP (Model Context Protocol) servers from Open WebUI
required_open_webui_version: 0.5.0
version: 1.0.0
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

# Config file for active server
MCP_CONFIG_FILE = os.path.expanduser("~/.open-webui/mcp-config.json")

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

def load_mcp_config() -> Dict:
    """Load MCP configuration from file"""
    if not os.path.exists(MCP_CONFIG_FILE):
        return {"active_server": ""}
    try:
        with open(MCP_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {"active_server": ""}

def save_mcp_config(config: Dict) -> None:
    """Save MCP configuration to file"""
    with open(MCP_CONFIG_FILE, "w") as f:
        json.dump(config, f)

class Pipe:
    def __init__(self):
        self.valves = self.Valves()
        
    class Valves(BaseModel):
        """Configuration options for the MCP Connector"""
        server_id: str = Field("", description="ID of the MCP server to use (leave empty to use the active server)")
        default_model: str = Field("", description="Default model to use if not specified in the request")
        timeout_seconds: int = Field(30, description="Timeout for MCP server requests (in seconds)")
        stream: bool = Field(False, description="Enable streaming responses (if supported by server)")

    async def pipe(self, body: dict, _user_: dict = None, _request_: Request = None, _event_emitter_: Optional[callable] = None) -> str:
        """
        Process chat messages through an MCP server or handle server management commands
        """
        # Check if this is a command message
        messages = body.get("messages", [])
        if messages and len(messages) > 0 and "content" in messages[-1]:
            user_message = messages[-1]["content"].strip()
            
            # Handle MCP commands
            if user_message.startswith("/mcp "):
                return await self._handle_command(user_message[5:])
            
            # Help command
            if user_message == "/mcp":
                return await self._show_help()
        
        # Continue with regular MCP server communication
        return await self._handle_chat(body, _event_emitter_)

    async def _handle_chat(self, body: dict, _event_emitter_: Optional[callable] = None) -> str:
        """Handle chat messages to MCP server"""
        # Load servers
        servers = load_mcp_servers()
        
        # Get active server ID
        server_id = self.valves.server_id
        if not server_id:
            # If no server specified in valves, use the active server from config
            config = load_mcp_config()
            server_id = config.get("active_server", "")
        
        # Check if we have a valid server
        if not server_id or server_id not in servers:
            return "No MCP server selected. Use '/mcp use <server_id>' to select a server or set one in the function configuration."
        
        server_config = servers[server_id]
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

    async def _handle_command(self, command: str) -> str:
        """Handle MCP commands"""
        parts = command.strip().split()
        if not parts:
            return "Invalid command. Use '/mcp help' to see available commands."
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Process commands
        if cmd == "list":
            return await self._list_servers()
        elif cmd == "popular":
            return await self._list_popular_servers()
        elif cmd == "add":
            if len(args) < 2:
                return "Error: Missing arguments. Usage: /mcp add <name> <url> [api_key] [default_model]"
            name = args[0]
            url = args[1]
            api_key = args[2] if len(args) > 2 else ""
            default_model = args[3] if len(args) > 3 else ""
            return await self._add_server(name, url, api_key, default_model)
        elif cmd == "addp":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: /mcp addp <server_id> [api_key] [default_model]"
            server_id = args[0]
            api_key = args[1] if len(args) > 1 else ""
            default_model = args[2] if len(args) > 2 else ""
            return await self._add_popular_server(server_id, api_key, default_model)
        elif cmd == "delete":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: /mcp delete <server_id>"
            server_id = args[0]
            return await self._delete_server(server_id)
        elif cmd == "use":
            if len(args) < 1:
                return "Error: Missing server_id. Usage: /mcp use <server_id>"
            server_id = args[0]
            return await self._use_server(server_id)
        elif cmd == "active":
            return await self._show_active_server()
        elif cmd == "help" or cmd == "":
            return await self._show_help()
        else:
            return f"Unknown command: {cmd}. Use '/mcp help' to see available commands."

    async def _show_help(self) -> str:
        """Show help for MCP commands"""
        help_text = "# MCP Connector Commands\n\n"
        help_text += "Use these commands to manage your MCP servers:\n\n"
        help_text += "- `/mcp list` - List all configured MCP servers\n"
        help_text += "- `/mcp popular` - List predefined popular MCP servers\n"
        help_text += "- `/mcp add <name> <url> [api_key] [default_model]` - Add a new MCP server\n"
        help_text += "- `/mcp addp <server_id> [api_key] [default_model]` - Add a predefined popular server\n"
        help_text += "- `/mcp delete <server_id>` - Delete a server\n"
        help_text += "- `/mcp use <server_id>` - Select a server to use\n"
        help_text += "- `/mcp active` - Show the currently active server\n"
        help_text += "- `/mcp help` - Show this help message\n\n"
        help_text += "Example usage:\n"
        help_text += "```\n/mcp popular\n/mcp addp brave_search your-api-key\n/mcp use server-id-from-list\n```"
        return help_text

    async def _list_servers(self) -> str:
        """List all configured MCP servers"""
        servers = load_mcp_servers()
        
        if not servers:
            return "No MCP servers configured. Use '/mcp add' to add one, or '/mcp popular' to see predefined options."
        
        # Get active server ID
        active_id = self.valves.server_id
        if not active_id:
            config = load_mcp_config()
            active_id = config.get("active_server", "")
        
        response = "## Configured MCP Servers\n\n"
        for server_id, server in servers.items():
            if server_id == active_id:
                response += f"### {server.get('name', 'Unnamed Server')} (ACTIVE)\n"
            else:
                response += f"### {server.get('name', 'Unnamed Server')}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server.get('url', 'Not set')}\n"
            response += f"- Default Model: {server.get('default_model', 'Not set')}\n"
            response += f"- API Key: {'Configured' if server.get('api_key') else 'Not set'}\n\n"
        
        response += "To use a server, use the command: `/mcp use server-id`"
        
        return response

    async def _list_popular_servers(self) -> str:
        """List popular predefined MCP servers that can be easily added"""
        response = "## Popular MCP Servers\n\n"
        response += "These are popular MCP servers that you can add to your configuration using the addp command.\n\n"
        
        for server_id, server in POPULAR_SERVERS.items():
            response += f"### {server['name']}\n"
            response += f"- ID: `{server_id}`\n"
            response += f"- URL: {server['url']}\n"
            response += f"- Description: {server['description']}\n"
            response += f"- API Key Required: {'Yes' if server['needs_api_key'] else 'No'}\n\n"
        
        response += "To add one of these servers, use the command:\n"
        response += "```\n/mcp addp server_id [api_key] [default_model]\n```\n"
        response += "For example:\n"
        response += "```\n/mcp addp brave_search your-api-key\n```\n"
        
        return response

    async def _add_popular_server(self, server_id: str, api_key: str = "", default_model: str = "") -> str:
        """Add a predefined popular MCP server"""
        servers = load_mcp_servers()
        
        if server_id not in POPULAR_SERVERS:
            return f"Error: No predefined server found with ID '{server_id}'. Use '/mcp popular' to see available options."
        
        server_info = POPULAR_SERVERS[server_id]
        
        # Check if API key is needed but not provided
        if server_info["needs_api_key"] and not api_key:
            return f"Error: The server '{server_info['name']}' requires an API key. Please provide one using: /mcp addp {server_id} your-api-key"
        
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
        
        # Set this as the active server
        config = load_mcp_config()
        config["active_server"] = new_server_id
        save_mcp_config(config)
        
        return f"MCP server '{server_info['name']}' added successfully and set as active!\n\nServer ID: `{new_server_id}`\n\nYou can now start chatting with this server."

    async def _add_server(self, name: str, url: str, api_key: str = "", default_model: str = "") -> str:
        """Add a new MCP server"""
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
        
        # Set this as the active server
        config = load_mcp_config()
        config["active_server"] = server_id
        save_mcp_config(config)
        
        return f"MCP server '{name}' added successfully and set as active!\n\nServer ID: `{server_id}`\n\nYou can now start chatting with this server."

    async def _delete_server(self, server_id: str) -> str:
        """Delete an MCP server"""
        servers = load_mcp_servers()
        
        if server_id not in servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server_name = servers[server_id].get("name", "Unnamed Server")
        
        # Check if this is the active server
        config = load_mcp_config()
        is_active = server_id == config.get("active_server", "")
        
        # Remove the server
        del servers[server_id]
        
        # Save the updated configuration
        save_mcp_servers(servers)
        
        # If we deleted the active server, clear it
        if is_active:
            config["active_server"] = ""
            save_mcp_config(config)
            return f"MCP server '{server_name}' deleted successfully! This was your active server, so you'll need to select a new one with '/mcp use <server_id>'."
        
        return f"MCP server '{server_name}' deleted successfully!"

    async def _use_server(self, server_id: str) -> str:
        """Select a server to use"""
        servers = load_mcp_servers()
        
        if server_id not in servers:
            return f"Error: No server found with ID '{server_id}'"
        
        server = servers[server_id]
        
        # Set as active server
        config = load_mcp_config()
        config["active_server"] = server_id
        save_mcp_config(config)
        
        return f"Now using MCP server '{server.get('name')}' as the active server.\n\nYou can now chat with this server!"

    async def _show_active_server(self) -> str:
        """Show the currently active server"""
        # Get active server ID from config or valves
        active_id = self.valves.server_id
        if not active_id:
            config = load_mcp_config()
            active_id = config.get("active_server", "")
        
        if not active_id:
            return "No active server selected. Use '/mcp use <server_id>' to select a server."
        
        servers = load_mcp_servers()
        if active_id not in servers:
            return f"Error: Active server ID '{active_id}' not found in server list."
        
        server = servers[active_id]
        
        response = "## Active MCP Server\n\n"
        response += f"**Name:** {server.get('name', 'Unnamed Server')}\n"
        response += f"**ID:** `{active_id}`\n"
        response += f"**URL:** {server.get('url', 'Not set')}\n"
        response += f"**Default Model:** {server.get('default_model', 'Not set')}\n"
        response += f"**API Key:** {'Configured' if server.get('api_key') else 'Not set'}\n\n"
        
        return response

    async def _handle_non_streaming(self, session, server_url, headers, payload, _event_emitter_):
        """Handle non-streaming request to MCP server"""
        # Try both path formats
        urls_to_try = [
            f"{server_url.rstrip('/')}/chat/completions",
            f"{server_url.rstrip('/')}/v1/chat/completions"
        ]
        
        for url in urls_to_try:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
                ) as response:
                    if response.status == 200:
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
                            continue  # Try next URL if no content received
                    
                    # If got an error other than 404, show it
                    if response.status != 404:
                        error_text = await response.text()
                        return f"Error connecting to MCP server: {response.status} - {error_text}"
            except Exception as e:
                # Log the error but continue to the next URL
                if _event_emitter_:
                    await _event_emitter_(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Error with {url}: {str(e)}",
                                "done": False,
                                "hidden": True
                            },
                        }
                    )
        
        # If we got here, all URLs failed
        return "Error: Could not connect to MCP server. The server may be unavailable or the URL may be incorrect."

    async def _handle_streaming(self, session, server_url, headers, payload, _event_emitter_):
        """Handle streaming request to MCP server"""
        # Try both path formats
        urls_to_try = [
            f"{server_url.rstrip('/')}/chat/completions",
            f"{server_url.rstrip('/')}/v1/chat/completions"
        ]
        
        for url in urls_to_try:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        full_response = ""
                        
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
                    
                    # If got an error other than 404, show it
                    if response.status != 404:
                        error_text = await response.text()
                        return f"Error connecting to MCP server: {response.status} - {error_text}"
            except Exception as e:
                # Log the error but continue to the next URL
                if _event_emitter_:
                    await _event_emitter_(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Error with {url}: {str(e)}",
                                "done": False,
                                "hidden": True
                            },
                        }
                    )
        
        # If we got here, all URLs failed
        return "Error: Could not connect to MCP server for streaming. The server may be unavailable or the URL may be incorrect."