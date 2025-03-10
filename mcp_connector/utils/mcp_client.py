"""
MCP Client utility module for connecting to MCP servers.
"""

import aiohttp
import json
import logging
from typing import Dict, List, Any, Optional, Union, AsyncIterator

# Configure logging
logger = logging.getLogger("mcp_client")

class MCPClient:
    """
    Client for interacting with MCP (Model Context Protocol) servers.
    Provides utility functions for common operations.
    """
    
    def __init__(
        self, 
        server_url: str, 
        api_key: Optional[str] = None,
        timeout: int = 30,
        debug: bool = False
    ):
        """
        Initialize the MCP client.
        
        Args:
            server_url: Base URL of the MCP server
            api_key: Optional API key for authentication
            timeout: Connection timeout in seconds
            debug: Enable debug logging
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.debug = debug
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for MCP API requests, including authentication if provided."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from the MCP server.
        
        Returns:
            List of model information dictionaries
        
        Raises:
            Exception: If the request fails
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.server_url}/v1/models",
                    headers=self.get_headers(),
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text[:100]}")
                    
                    data = await response.json()
                    return data.get("data", [])
            
            except Exception as e:
                if self.debug:
                    logger.error(f"Error listing models: {str(e)}")
                raise Exception(f"Failed to list models: {str(e)}")
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get information about a specific model.
        
        Args:
            model_id: ID of the model to get information for
            
        Returns:
            Model information dictionary
            
        Raises:
            Exception: If the request fails
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.server_url}/v1/models/{model_id}",
                    headers=self.get_headers(),
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text[:100]}")
                    
                    return await response.json()
            
            except Exception as e:
                if self.debug:
                    logger.error(f"Error getting model info: {str(e)}")
                raise Exception(f"Failed to get model info: {str(e)}")
    
    async def chat_completion(
        self, 
        model_id: str, 
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[str]]:
        """
        Send a chat completion request to the MCP server.
        
        Args:
            model_id: ID of the model to use
            messages: List of message dictionaries
            stream: Whether to stream the response
            temperature: Optional temperature parameter
            max_tokens: Optional max tokens parameter
            **kwargs: Additional parameters to include in the request
            
        Returns:
            Response dictionary for non-streaming requests,
            or an async iterator for streaming requests
            
        Raises:
            Exception: If the request fails
        """
        payload = {
            "model": model_id,
            "messages": messages,
            "stream": stream
        }
        
        # Add optional parameters if provided
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        # Add any other parameters
        payload.update(kwargs)
        
        if stream:
            return await self._stream_chat_completion(payload)
        else:
            return await self._non_stream_chat_completion(payload)
    
    async def _stream_chat_completion(self, payload: Dict[str, Any]) -> AsyncIterator[str]:
        """Handle streaming chat completion request."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.server_url}/v1/chat/completions",
                    json=payload,
                    headers=self.get_headers(),
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text[:100]}")
                    
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith('data: '):
                                line_str = line_str[6:]
                            if line_str and line_str != '[DONE]':
                                yield line_str
            
            except Exception as e:
                if self.debug:
                    logger.error(f"Error in streaming chat completion: {str(e)}")
                raise Exception(f"Streaming chat completion failed: {str(e)}")
    
    async def _non_stream_chat_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle non-streaming chat completion request."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.server_url}/v1/chat/completions",
                    json=payload,
                    headers=self.get_headers(),
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text[:100]}")
                    
                    return await response.json()
            
            except Exception as e:
                if self.debug:
                    logger.error(f"Error in chat completion: {str(e)}")
                raise Exception(f"Chat completion failed: {str(e)}")

    async def ping(self) -> bool:
        """
        Check if the MCP server is reachable.
        
        Returns:
            True if the server is reachable, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.server_url}/v1/models",
                    headers=self.get_headers(),
                    timeout=self.timeout / 2  # Use shorter timeout for ping
                ) as response:
                    return response.status == 200
        except:
            return False