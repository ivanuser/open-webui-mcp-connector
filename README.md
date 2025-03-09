# MCP Connector for Open WebUI

This repository provides integration between Open WebUI and MCP (Model Context Protocol) servers, allowing you to connect to any MCP-compatible server directly from your Open WebUI interface.

## Features

- Connect to any OpenAI API-compatible MCP servers from Open WebUI
- Easy setup with predefined popular MCP servers
- Manage multiple MCP server configurations
- Test connectivity to servers
- Secure API key storage
- Support for streaming responses
- Straightforward UI configuration

## Installation

### Step 1: Install Both Functions

1. Download the Function files:
   - `mcp_pipe.py` - The main connector Pipe Function
   - `mcp_action.py` - The server management Action Function

2. In Open WebUI, go to **Admin > Settings > Functions**

3. Click "Import" and select the downloaded files

4. Enable both imported Functions

### Alternative: Direct Installation from GitHub

1. In Open WebUI, go to **Admin > Settings > Functions**

2. Click "New" and select "Import from URL"

3. Enter the URLs of the Function files:
   - Pipe Function: `https://raw.githubusercontent.com/ivanuser/open-webui-mcp-connector/main/mcp_pipe.py`
   - Action Function: `https://raw.githubusercontent.com/ivanuser/open-webui-mcp-connector/main/mcp_action.py`

4. Enable both imported Functions

## Usage

### Step 1: Add an MCP Server

1. Open a new chat and select any model

2. Use the MCP Server Manager commands to add a server:

   - List popular predefined servers:
     ```
     /list_popular_servers
     ```

   - Add a popular server (like Brave Search):
     ```
     /add_popular_server server_id="brave_search" api_key="your-api-key" default_model="default-model-name"
     ```

   - Or add a custom server:
     ```
     /add_server name="My MCP Server" url="https://example.com/api" api_key="your-api-key" default_model="default-model-name"
     ```

3. The command will output a server ID. **Copy this ID** - you'll need it in the next step.

### Step 2: Configure the MCP Connector

1. Go to **Admin > Settings > Functions**

2. Find the "MCP Connector" function and click the gear icon (settings)

3. In the "server_id" field, paste the server ID you copied in Step 1

4. Optionally configure other settings:
   - default_model: Override the server's default model
   - timeout_seconds: Adjust request timeout (default: 30 seconds)
   - stream: Enable/disable streaming responses (default: false)

5. Click "Save"

### Step 3: Use the MCP Connector

1. Start a new chat

2. From the model selection dropdown, select "MCP Connector"

3. Start chatting normally! Your messages will be sent to the configured MCP server

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

You can view the complete list with detailed information using the `/list_popular_servers` command.

## Managing Your Servers

- **List all servers**:
  ```
  /list_servers
  ```

- **Delete a server**:
  ```
  /delete_server server_id="server-id-from-list"
  ```

## Troubleshooting

If you encounter issues:

1. **No MCP server selected error**: Make sure you've added a server and configured the MCP Connector with the correct server ID.

2. **Connection errors**: Check that the server URL is correct and your API key is valid.

3. **Function not working**: Make sure both functions are properly imported and enabled in Admin > Settings > Functions.

4. **Command not recognized**: Try typing the command in a new chat with a default model (not the MCP Connector).

5. **Server responds with errors**: Check that the server supports the OpenAI-compatible chat completions endpoint.

## License

MIT