# MCP Connector for Open WebUI

This repository provides integration between Open WebUI and MCP (Model Context Protocol) servers, allowing you to connect to any MCP-compatible server directly from your Open WebUI interface.

## Features

- Connect to any OpenAI API-compatible MCP servers from Open WebUI
- Easy setup with predefined popular MCP servers
- Manage multiple MCP server configurations
- Test connectivity to servers
- Secure API key storage
- Support for streaming responses
- Easy-to-use interface through text commands

## Installation

### Method 1: Manual Installation

1. Download the Pipe Function file:
   - `mcp_pipe.py` - The main connector Pipe Function with built-in server management

2. In Open WebUI, go to **Admin > Settings > Functions**

3. Click "Import" and select the downloaded file

4. Enable the imported Function

### Method 2: Direct Installation from GitHub

1. In Open WebUI, go to **Admin > Settings > Functions**

2. Click "New" and select "Import from URL"

3. Enter the URL of the Function file:
   - `https://raw.githubusercontent.com/ivanuser/open-webui-mcp-connector/main/mcp_pipe.py`

4. Enable the imported Function

## Usage

### Setting Up MCP Servers

1. Enable the "MCP Connector" Pipe Function in **Admin > Settings > Functions**

2. Start a new chat using any model

3. Use the following commands to manage your MCP servers:

   - **Get help and list of commands**:
     ```
     !mcp help
     ```

   - **List predefined popular servers**:
     ```
     !mcp list_popular
     ```

   - **Add a predefined popular server**:
     ```
     !mcp add_popular brave_search your-api-key
     ```

   - **Add a custom server**:
     ```
     !mcp add myserver https://example.com/api your-api-key default-model
     ```
   
   - **List all configured servers**:
     ```
     !mcp list
     ```
   
   - **Select server for current session**:
     ```
     !mcp use server-id-from-list
     ```
   
   - **Test a server connection**:
     ```
     !mcp test server-id
     ```
   
   - **Get available models**:
     ```
     !mcp models server-id
     ```
   
   - **Update a server**:
     ```
     !mcp update server-id field value
     ```
     Fields can be: name, url, api_key, default_model
   
   - **Delete a server**:
     ```
     !mcp delete server-id
     ```

### Using MCP Servers

1. Once you've configured and selected a server with `!mcp use server-id`, you can start chatting with it immediately.

2. The MCP Connector will now handle your messages and send them to the selected MCP server.

## Predefined Popular Servers

The connector includes a list of popular predefined MCP servers that you can easily add to your configuration:

- **Anthropic Reference Implementation** - Official Anthropic MCP server with core features
- **Brave Search** - Web and local search using Brave's Search API
- **Kagi Search** - Search the web using Kagi's search API
- **Tavily Search** - Search engine for AI agents by Tavily
- **OpenAI** - OpenAI models integration
- **Filesystem** - Local filesystem access (requires local setup)
- **GitHub** - GitHub API integration (requires local setup)
- **Memory** - Knowledge graph-based memory system (requires local setup)

You can view the complete list with detailed information using the `!mcp list_popular` command.

## Example Workflow

Here's a full example of how to set up and use an MCP server:

1. List popular servers:
   ```
   !mcp list_popular
   ```

2. Add a Brave Search server:
   ```
   !mcp add_popular brave_search your-api-key
   ```

3. List your configured servers:
   ```
   !mcp list
   ```

4. Select the server to use (replace server-id with the actual ID from the list):
   ```
   !mcp use server-id
   ```

5. Now you can chat directly with the Brave Search MCP server!

## Compatibility

This connector works with any server that implements the OpenAI API-compatible endpoints:

- `/v1/chat/completions` - Used for chat interactions
- `/v1/models` - Used for listing available models

## Troubleshooting

If you encounter issues:

1. Check that the server URL is correct and includes the protocol (http:// or https://)
2. Verify your API key is valid
3. Ensure the server supports the OpenAI-compatible chat completions endpoint
4. Test the connection using the `!mcp test server-id` command
5. Check for error messages in the Open WebUI logs

## License

MIT