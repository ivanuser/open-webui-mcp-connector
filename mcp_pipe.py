"""
title: MCP Connector
author: Open WebUI Contributor
description: Connect to MCP (Model Context Protocol) servers from Open WebUI
required_open_webui_version: 0.5.0
version: 0.3.1
license: MIT
"""

from pydantic import BaseModel, Field
from fastapi import Request
import aiohttp
import json
import os
from typing import Dict, List, Optional

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

class Pipe:
    def __init__(self):
        self.valves = self.Valves()
        
    class Valves(BaseModel):
        server_id: str = Field("", description="ID of the MCP server to use (set up via the MCP Manager)")
        default_model: str = Field("", description="Default model to use if not specified in the request")
        timeout_seconds: int = Field(30, description="Timeout for MCP server requests (in seconds)")
        stream: bool = Field(False, description="Enable streaming responses (if supported by server)")

    async def pipe(self, body: dict, _user_: dict = None, _request_: Request = None, _event_emitter_: Optional[callable] = None) -> str:
        """
        Process chat messages through an MCP server
        
        This function sends the chat messages to the configured MCP server 
        and returns the model's response.
        """
        # Load server configurations
        servers = load_mcp_servers()
        
        # Check if the server exists
        if not self.valves.server_id or self.valves.server_id not in servers:
            return "Error: No MCP server selected. Please configure a server via Admin > Settings > Functions, then click the gear icon on this function and enter a valid server ID."

        server_config = servers[self.valves.server_id]
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

    async def _handle_non_streaming(self, session, server_url, headers, payload, _event_emitter_):
        """Handle non-streaming request to MCP server"""
        async with session.post(
            f"{server_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
        ) as response:
            if response.status != 200:
                # Try the alternative path format if the first one fails
                try:
                    async with session.post(
                        f"{server_url.rstrip('/')}/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
                    ) as alt_response:
                        if alt_response.status != 200:
                            error_text = await alt_response.text()
                            return f"Error connecting to MCP server: {alt_response.status} - {error_text}"
                        
                        response_json = await alt_response.json()
                except Exception as e:
                    error_text = await response.text()
                    return f"Error connecting to MCP server: {response.status} - {error_text}"
            else:
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
        
        try:
            async with session.post(
                f"{server_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
            ) as response:
                if response.status != 200:
                    # Try the alternative path format if the first one fails
                    async with session.post(
                        f"{server_url.rstrip('/')}/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.valves.timeout_seconds)
                    ) as alt_response:
                        if alt_response.status != 200:
                            error_text = await alt_response.text()
                            return f"Error connecting to MCP server: {alt_response.status} - {error_text}"
                        
                        response = alt_response
                
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
        except Exception as e:
            return f"Error in streaming: {str(e)}"
        
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