"""
title: MCP Connector
author: Open WebUI Contributor
description: Connect to MCP (Model Context Protocol) servers from Open WebUI
required_open_webui_version: 0.5.0
version: 1.1.0
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

# Predefined list of popular MCP servers with their correct endpoints
POPULAR_SERVERS = {
    "anthropic_official": {
        "name": "Anthropic Reference Implementation",
        "url": "https://mcp.anthropic.com/v1",
        "description": "Official Anthropic MCP server with core features",
        "needs_api_key": True,
        "chat_endpoint": "chat/completions"
    },
    "brave_search": {
        "name": "Brave Search",
        "url": "https://mcp.brave.com/v1",
        "description": "Web and local search using Brave's Search API",
        "needs_api_key": True,
        "chat_endpoint": "search" 
    },
    "kagi_search": {
        "name": "Kagi Search",
        "url": "https://kagi.com/api/v1",
        "description": "Search the web using Kagi's search API",
        "needs_api_key": True,
        "chat_endpoint": "chat/completions"
    },
    "tavily": {
        "name": "Tavily Search",
        "url": "https://api.tavily.com/v1",
        "description": "Search engine for AI agents by Tavily",
        "needs_api_key": True,
        "chat_endpoint": "chat/completions"
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1",
        "description": "OpenAI models integration",
        "needs_api_key": True,
        "chat_endpoint": "chat/completions"
    },
    "filesystem": {
        "name": "Filesystem",
        "url": "http://localhost:3000",
        "description": "Local filesystem access (requires local server setup)",
        "needs_api_key": False,
        "chat_endpoint": "chat/completions"
    },
    "github": {
        "name": "GitHub",
        "url": "http://localhost:3001",
        "description": "GitHub API integration (requires local server setup)",
        "needs_api_key": True,
        "chat_endpoint": "chat/completions"
    },
    "memory": {
        "name": "Memory",
        "url": "http://localhost:3002",
        "description": "Knowledge graph-based memory system (requires local server setup)",
        "needs_api_key": False,
        "chat_endpoint": "chat/completions"
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

def is_brave_search(server_url: str) -> bool:
    """Check if the server is Brave Search"""
    return "brave.com" in server_url.lower()

def get_chat_endpoint(server_url: str) -> str:
    """Get the appropriate chat endpoint for a server"""
    if is_brave_search(server_url):
        return "search"
    return "chat/completions"

class Pipe:
    def __init__(self):
        self.valves = self.Valves()
        
    class Valves(BaseModel):
        """Configuration options for the MCP Connector"""
        server_id: str = Field("", description="ID of the MCP server to use (leave empty to use the active server)")
        default_model: str = Field("", description="Default model to use if not specified in the request")
        timeout_seconds: int = Field(30, description="Timeout for MCP server requests (in seconds)")
        stream: bool = Field(False, description="Enable streaming responses (if supported by server)")
        debug: bool = Field(False, description="Enable debug mode for more detailed error information")

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
        
        # Handle Brave Search specifically
        if is_brave_search(server_url):
            return await self._handle_brave_search(body, server_url, api_key, _event_emitter_)
        
        # Handle general MCP servers
        return await self._handle_general_mcp(body, server_config, _event_emitter_)

    async def _handle_brave_search(self, body, server_url, api_key, _event_emitter_):
        """Special handler for Brave Search"""
        # Extract messages
        messages = body.get("messages", [])
        
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            return "No search query found. Please ask a question or provide a search term."
        
        # Configure request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if api_key:
            headers["X-Subscription-Token"] = api_key
        
        # Prepare search payload for Brave
        search_payload = {
            "q": user_message,
            "count": 5
        }
        
        # Send request to Brave Search API
        try:
            async with aiohttp.ClientSession() as session:
                search_url = f"{server_url.rstrip('/')}/search"
                
                if self.valves.debug:
                    debug_info = f"Debug: Connecting to Brave Search API at {search_url}\n"
                    debug_info += f"Debug: Headers: {json.dumps(headers)}\n"
                    debug_info += f"Debug: Payload: {json.dumps(search_payload)}\n"
                    
                    # Emit debug status if event emitter is available
                    if _event_emitter_:
                        await _event_emitter_(
                            {
                                "type": "status",
                                "data": {
                                    "description": debug_info,
                                    "done": False,
                                    "hidden": False
                                },
                            }
                        )
                
                async with session.get(
                    search_url,
                    headers=headers,
                    params=search_payload,
                    timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Error searching with Brave Search: {response.status} - {error_text}"
                    
                    search_results = await response.json()
                    
                    # Format the response
                    response_text = f"# Search Results for: {user_message}\n\n"
                    
                    # Add web results
                    if "web" in search_results and "results" in search_results["web"]:
                        response_text += "## Web Results\n\n"
                        
                        for i, result in enumerate(search_results["web"]["results"], 1):
                            title = result.get("title", "No Title")
                            url = result.get("url", "")
                            description = result.get("description", "No Description")
                            
                            response_text += f"### {i}. {title}\n"
                            response_text += f"{description}\n"
                            response_text += f"URL: {url}\n\n"
                    
                    # Add news results if available
                    if "news" in search_results and "results" in search_results["news"]:
                        response_text += "## News Results\n\n"
                        
                        for i, result in enumerate(search_results["news"]["results"], 1):
                            title = result.get("title", "No Title")
                            url = result.get("url", "")
                            description = result.get("description", "No Description")
                            
                            response_text += f"### {i}. {title}\n"
                            response_text += f"{description}\n"
                            response_text += f"URL: {url}\n\n"
                    
                    # Emit completion status if event emitter is available
                    if _event_emitter_:
                        await _event_emitter_(
                            {
                                "type": "status",
                                "data": {
                                    "description": "Search results received from Brave Search",
                                    "done": True,
                                    "hidden": False
                                },
                            }
                        )
                    
                    return response_text
        
        except Exception as e:
            error_details = f"Error: Failed to search with Brave Search: {str(e)}"
            
            if self.valves.debug:
                import traceback
                error_details += f"\n\nDebug Traceback:\n{traceback.format_exc()}"
            
            return error_details

    async def _handle_general_mcp(self, body, server_config, _event_emitter_):
        """Handle general MCP servers (non-Brave)"""
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
        
        # Send request to MCP server
        try:
            async with aiohttp.ClientSession() as session:
                # Try multiple URL path formats
                urls_to_try = [
                    f"{server_url.rstrip('/')}/chat/completions",
                    f"{server_url.rstrip('/')}/v1/chat/completions"
                ]
                
                if self.valves.debug:
                    debug_info = f"Debug: Will try these URLs: {urls_to_try}\n"
                    debug_info += f"Debug: Headers: {json.dumps(headers)}\n"
                    debug_info += f"Debug: Streaming enabled: {self.valves.stream}\n"
                    
                    # Emit debug status if event emitter is available
                    if _event_emitter_:
                        await _event_emitter_(
                            {
                                "type": "status",
                                "data": {
                                    "description": debug_info,
                                    "done": False,
                                    "hidden": False
                                },
                            }
                        )
                
                # First try with streaming if enabled
                if self.valves.stream:
                    streaming_result = await self._try_streaming(session, urls_to_try, headers, mcp_payload, _event_emitter_)
                    if not streaming_result.startswith("Error:"):
                        return streaming_result
                    
                    # If streaming failed, try without streaming
                    if self.valves.debug and _event_emitter_:
                        await _event_emitter_(
                            {
                                "type": "status",
                                "data": {
                                    "description": "Streaming failed, trying without streaming",
                                    "done": False,
                                    "hidden": False
                                },
                            }
                        )
                
                # Try non-streaming
                mcp_payload["stream"] = False
                for url in urls_to_try:
                    try:
                        if self.valves.debug and _event_emitter_:
                            await _event_emitter_(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": f"Trying URL: {url}",
                                        "done": False,
                                        "hidden": False
                                    },
                                }
                            )
                        
                        async with session.post(
                            url,
                            headers=headers,
                            json=mcp_payload,
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
                                error_message = f"Error connecting to MCP server: {response.status} - {error_text}"
                                
                                if self.valves.debug:
                                    error_message += f"\nURL: {url}\nHeaders: {headers}\nPayload: {json.dumps(mcp_payload)}"
                                    
                                return error_message
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
                error_msg = "Error: Could not connect to MCP server. The server may be unavailable or the URL may be incorrect."
                
                if self.valves.debug:
                    error_msg += f"\n\nDebug info:\nServer URL: {server_url}\nTried URLs: {urls_to_try}"
                    
                return error_msg
        except Exception as e:
            error_details = f"Error: Failed to communicate with the MCP server: {str(e)}"
            
            if self.valves.debug:
                import traceback
                error_details += f"\n\nDebug Traceback:\n{traceback.format_exc()}"
                
            return error_details

    async def _try_streaming(self, session, urls_to_try, headers, payload, _event_emitter_):
        """Try streaming with multiple URL formats"""
        for url in urls_to_try:
            try:
                if self.valves.debug and _event_emitter_:
                    await _event_emitter_(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Trying streaming with URL: {url}",
                                "done": False,
                                "hidden": False
                            },
                        }
                    )
                
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
                                "description": f"Error with streaming {url}: {str(e)}",
                                "done": False,
                                "hidden": True
                            },
                        }
                    )
        
        # If we got here, all URLs failed for streaming
        return "Error: Could not connect to MCP server for streaming. The server may be unavailable or the URL may be incorrect."

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
                return "Error: Missing arguments. Usage: /mcp add <n> <url> [api_key] [default_model]"
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
        elif cmd == "debug":
            if len(args) > 0 and args[0].lower() in ("on", "true", "1", "yes"):
                self.valves.debug = True
                return "Debug mode enabled. You will see detailed error information."
            elif len(args) > 0 and args[0].lower() in ("off", "false", "0", "no"):
                self.valves.debug = False
                return "Debug mode disabled."
            else:
                return f"Debug mode is currently {'enabled' if self.valves.debug else 'disabled'}. Use '/mcp debug on' or '/mcp debug off' to change."
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
        help_text += "- `/mcp add <n> <url> [api_key] [default_model]` - Add a new MCP server\n"
        help_text += "- `/mcp addp <server_id> [api_key] [default_model]` - Add a predefined popular server\n"
        help_text += "- `/mcp delete <server_id>` - Delete a server\n"
        help_text += "- `/mcp use <server_id>` - Select a server to use\n"
        help_text += "- `/mcp active` - Show the currently active server\n"
        help_text += "- `/mcp debug on|off` - Enable/disable debug mode for troubleshooting\n"
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
            "default_model": default_model,
            "chat_endpoint": server_info.get("chat_endpoint", "chat/completions")
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
        
        # Determine the chat endpoint based on URL
        chat_endpoint = get_chat_endpoint(url)
        
        # Add the server to the configuration
        servers[server_id] = {
            "name": name,
            "url": url,
            "api_key": api_key,
            "default_model": default_model,
            "chat_endpoint": chat_endpoint
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
        response += f"**API Key:** {'Configured' if server.get('api_key') else 'Not set'}\n"
        response += f"**Chat Endpoint:** {server.get('chat_endpoint', 'chat/completions')}\n\n"
        
        if self.valves.debug:
            response += "**Debug Mode:** Enabled\n\n"
        
        return response