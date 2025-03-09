# MCP Connector for Open WebUI

This repository provides integration between Open WebUI and MCP (Model Context Protocol) servers, allowing you to connect to any MCP-compatible server directly from your Open WebUI interface.

## Features

- Connect to any OpenAI API-compatible MCP servers from Open WebUI
- Easy setup with predefined popular MCP servers
- Manage multiple MCP server configurations with simple commands
- Test connectivity to servers
- Secure API key storage
- Support for streaming responses
- All-in-one solution with a single function

## Installation

### Option 1: Manual Installation

1. Download the Function file:
   - `mcp_pipe.py` - The all-in-one MCP Connector

2. In Open WebUI, go to **Admin > Settings > Functions**

3. Click "Import" and select the downloaded file

4. Enable the imported Function

### Option 2: Direct Installation from GitHub

1. In Open WebUI, go to **Admin > Settings > Functions**

2. Click "New" and select "Import from URL"

3. Enter this URL:
   ```
   https://raw.githubusercontent.com/ivanuser/open-webui-mcp-connector/main/mcp_pipe.py
   ```

4. Enable the imported Function

## Usage

### Step 1: Add an MCP Server

1. Start a new chat and select the "MCP Connector" from the model dropdown

2. View the list of available popular servers:
   ```
   /mcp popular
   ```

3. Add a server (for example, Brave Search):
   ```
   /mcp addp brave_search your-api-key
   ```
   This automatically sets the server as your active server

4. Or add a custom server:
   ```
   /mcp add MyServer https://example.com/api your-api-key
   ```

### Step 2: Use Your MCP Server

Once you've added a server, you can just chat normally! Your messages will be sent to the active MCP server automatically. No additional configuration needed.

### Managing Your Servers

- **List all servers**:
  ```
  /mcp list
  ```

- **Switch to a different server**:
  ```
  /mcp use server-id-from-list
  ```

- **Check which server is active**:
  ```
  /mcp active
  ```

- **Delete a server**:
  ```
  /mcp delete server-id
  ```

- **Get help with commands**:
  ```
  /mcp help
  ```

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

View the complete list with detailed information using the `/mcp popular` command.

## Advanced Configuration

You can also configure the MCP Connector through the Admin interface:

1. Go to **Admin > Settings > Functions**

2. Find the "MCP Connector" function and click the gear icon (settings)

3. Configure these options:
   - **server_id** - Override the active server with a specific server ID
   - **default_model** - Set a default model to use
   - **timeout_seconds** - Adjust request timeout (default: 30 seconds)
   - **stream** - Enable/disable streaming responses (default: false)

## Example Workflow

```
You: /mcp popular
Bot: [Lists all popular MCP servers]

You: /mcp addp brave_search your-api-key
Bot: MCP server 'Brave Search' added successfully and set as active!

You: What's the weather in Florida?
Bot: [Brave Search results about weather in Florida]

You: /mcp addp kagi_search your-kagi-api-key
Bot: MCP server 'Kagi Search' added successfully and set as active!

You: What are the best books on machine learning?
Bot: [Kagi Search results about machine learning books]
```

## Troubleshooting

If you encounter issues:

1. Make sure the MCP Connector function is properly imported and enabled
2. Check that you've added and selected a server
3. Verify that your API key is correct
4. Try adding a server again if you're having connection issues
5. Make sure you're chatting with the MCP Connector model, not a different model

## License

MIT