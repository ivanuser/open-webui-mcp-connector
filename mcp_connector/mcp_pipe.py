"""
MCP Connector for Open WebUI

This pipe function allows connecting to MCP (Model Context Protocol) servers
and making them available as models in Open WebUI.
"""

from pydantic import BaseModel, Field
import requests
import json
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_connector")

class Pipe:
    """
    Pipe function to connect Open WebUI with MCP (Model Context Protocol) servers.
    """
    
    class Valves(BaseModel):
        """Configuration options for the MCP connector pipe."""
        
        NAME_PREFIX: str = Field(
            default="MCP/",
            description="Prefix to be added before model names."
        )
        
        MCP_SERVERS: str = Field(
            default="[]", 
            description="JSON array of MCP server configurations. Each server should have 'name', 'url', and optional 'api_key' fields."
        )
        
        CONNECTION_TIMEOUT: int = Field(
            default=30,
            description="Timeout in seconds for MCP server connections."
        )
        
        DEBUG_MODE: bool = Field(
            default=False,
            description="Enable detailed debug logging."
        )
    
    def __init__(self):
        """Initialize the MCP connector pipe."""
        self.valves = self.Valves()
        self.servers = []
        self._load_servers()
    
    def _load_servers(self):
        """Load MCP server configurations from the valves."""
        try:
            self.servers = json.loads(self.valves.MCP_SERVERS)
            if self.valves.DEBUG_MODE:
                logger.info(f"Loaded {len(self.servers)} MCP servers")
        except json.JSONDecodeError:
            logger.error("Failed to parse MCP_SERVERS JSON configuration")
            self.servers = []
    
    def pipes(self):
        """
        Return a list of available MCP models from configured servers.
        Each server's models will be listed as separate models in Open WebUI.
        """
        self._load_servers()  # Refresh server list in case it was updated
        
        if not self.servers:
            return [
                {
                    "id": "mcp_not_configured",
                    "name": f"{self.valves.NAME_PREFIX}Not Configured"
                }
            ]
        
        all_models = []
        
        for server in self.servers:
            server_name = server.get("name", "Unknown Server")
            server_url = server.get("url", "")
            api_key = server.get("api_key", "")
            
            if not server_url:
                all_models.append({
                    "id": f"mcp_error_{server_name.replace(' ', '_').lower()}",
                    "name": f"{self.valves.NAME_PREFIX}{server_name} - Missing URL"
                })
                continue
            
            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                # Attempt to fetch models from the MCP server
                response = requests.get(
                    f"{server_url}/v1/models",
                    headers=headers,
                    timeout=self.valves.CONNECTION_TIMEOUT
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    models = models_data.get("data", [])
                    
                    for model in models:
                        model_id = model.get("id", "unknown")
                        model_name = model.get("name", model_id)
                        
                        all_models.append({
                            "id": f"mcp_{server_name.replace(' ', '_').lower()}.{model_id}",
                            "name": f"{self.valves.NAME_PREFIX}{server_name}/{model_name}"
                        })
                else:
                    error_message = response.text[:100] if response.text else "No error details"
                    if self.valves.DEBUG_MODE:
                        logger.error(f"Error fetching models from {server_name}: {response.status_code} - {error_message}")
                    
                    all_models.append({
                        "id": f"mcp_error_{server_name.replace(' ', '_').lower()}",
                        "name": f"{self.valves.NAME_PREFIX}{server_name} - Error ({response.status_code})"
                    })
            
            except requests.exceptions.RequestException as e:
                if self.valves.DEBUG_MODE:
                    logger.error(f"Connection error with {server_name}: {str(e)}")
                
                all_models.append({
                    "id": f"mcp_error_{server_name.replace(' ', '_').lower()}",
                    "name": f"{self.valves.NAME_PREFIX}{server_name} - Connection Error"
                })
        
        return all_models if all_models else [
            {
                "id": "mcp_no_models",
                "name": f"{self.valves.NAME_PREFIX}No Models Found"
            }
        ]
    
    async def pipe(self, body: dict, __user__: Optional[dict] = None) -> Union[dict, str]:
        """
        Process the chat completion request and forward it to the appropriate MCP server.
        
        Args:
            body: The request body containing the chat completion request.
            __user__: Optional user information.
            
        Returns:
            The response from the MCP server or an error message.
        """
        if self.valves.DEBUG_MODE:
            logger.info(f"Received request for model: {body.get('model', 'unknown')}")
        
        model = body.get("model", "")
        
        # Parse server and model from the format: mcp_servername.model_id
        if not model.startswith("mcp_"):
            return {"error": "Invalid MCP model format"}
        
        if "error" in model:
            error_message = next((m["name"] for m in self.pipes() if m["id"] == model), "Unknown error")
            return {"error": error_message}
        
        parts = model.split(".", 1)
        if len(parts) != 2:
            return {"error": "Invalid MCP model format"}
        
        server_id = parts[0].replace("mcp_", "")
        model_id = parts[1]
        
        # Find the server configuration
        server = next((s for s in self.servers if s.get("name", "").replace(" ", "_").lower() == server_id), None)
        
        if not server:
            return {"error": f"MCP server '{server_id}' not found"}
        
        server_url = server.get("url", "")
        api_key = server.get("api_key", "")
        
        if not server_url:
            return {"error": f"MCP server '{server_id}' has no URL configured"}
        
        # Remove our custom prefix from the model field to get the actual model ID
        payload = {**body, "model": model_id}
        
        # Set up headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Handle streaming vs non-streaming requests differently
        streaming = payload.get("stream", False)
        
        try:
            if streaming:
                return await self._handle_streaming_request(server_url, headers, payload)
            else:
                return await self._handle_non_streaming_request(server_url, headers, payload)
                
        except Exception as e:
            error_message = str(e)
            if self.valves.DEBUG_MODE:
                logger.error(f"Error processing request: {error_message}")
            return {"error": f"MCP connection error: {error_message}"}
    
    async def _handle_streaming_request(self, server_url: str, headers: dict, payload: dict) -> Any:
        """Handle a streaming request to the MCP server."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{server_url}/v1/chat/completions",
                    json=payload, 
                    headers=headers,
                    timeout=self.valves.CONNECTION_TIMEOUT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text[:100]}")
                    
                    # Return an async iterator for streaming
                    async def response_iterator():
                        async for line in response.content:
                            if line:
                                # Process the line (removing 'data: ' prefix if present)
                                line_str = line.decode('utf-8').strip()
                                if line_str.startswith('data: '):
                                    line_str = line_str[6:]
                                if line_str and line_str != '[DONE]':
                                    yield line_str
                    
                    return response_iterator()
            
            except asyncio.TimeoutError:
                raise Exception(f"Connection timeout after {self.valves.CONNECTION_TIMEOUT} seconds")
            except aiohttp.ClientError as e:
                raise Exception(f"Connection error: {str(e)}")
    
    async def _handle_non_streaming_request(self, server_url: str, headers: dict, payload: dict) -> dict:
        """Handle a non-streaming request to the MCP server."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{server_url}/v1/chat/completions",
                    json=payload, 
                    headers=headers,
                    timeout=self.valves.CONNECTION_TIMEOUT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text[:100]}")
                    
                    return await response.json()
            
            except asyncio.TimeoutError:
                raise Exception(f"Connection timeout after {self.valves.CONNECTION_TIMEOUT} seconds")
            except aiohttp.ClientError as e:
                raise Exception(f"Connection error: {str(e)}")
