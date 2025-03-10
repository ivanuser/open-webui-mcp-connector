# MCP Connector for Open WebUI

A Pipe Function for Open WebUI that connects to MCP (Model Context Protocol) servers, allowing you to use MCP-compatible models directly within Open WebUI.

## Features

- 🌐 Connect to multiple MCP servers simultaneously
- 🔑 Support for API key authentication
- 🧠 Automatic model discovery from MCP servers
- 🔄 Support for streaming responses
- 🛡️ Robust error handling and timeout management
- 🔍 Debug mode for troubleshooting

## What is MCP?

MCP (Model Context Protocol) is a protocol used for AI model interactions. It provides a standardized way to interact with various AI models, similar to the OpenAI API specification.

## Installation

### Method 1: Install from GitHub

```bash
pip install git+https://github.com/ivanuser/open-webui-mcp-connector.git
```

### Method 2: Install through Open WebUI

1. Navigate to Workspace > Functions in Open WebUI
2. Click "Import Function"
3. Enter the GitHub URL: `https://github.com/ivanuser/open-webui-mcp-connector`
4. Click "Import"

## Usage

Once installed, you'll need to configure your MCP servers:

1. Navigate to Workspace > Functions in Open WebUI
2. Find the "MCP Connector" function and click the edit (pencil) icon
3. Configure your MCP servers in the "MCP_SERVERS" field using the JSON format:

```json
[
    {
        "name": "MyMCP Server 1",
        "url": "https://mcp.example.com",
        "api_key": "your_api_key_here"
    },
    {
        "name": "MyMCP Server 2",
        "url": "https://another-mcp.example.com",
        "api_key": "another_api_key_here"
    }
]
```

4. Click "Save"
5. Enable the function by toggling the switch

After configuration, your MCP server models will appear in the model selection dropdown with the prefix "MCP/" (you can customize this prefix in the settings).

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| NAME_PREFIX | Prefix added to model names in the UI | "MCP/" |
| MCP_SERVERS | JSON array of server configurations | "[]" |
| CONNECTION_TIMEOUT | Timeout in seconds for server connections | 30 |
| DEBUG_MODE | Enable detailed debug logging | false |

## Server Configuration Format

Each server in the `MCP_SERVERS` array should have the following format:

```json
{
    "name": "Display Name",
    "url": "https://server-url.example.com",
    "api_key": "optional_api_key"
}
```

- `name`: A user-friendly name for the server (will appear in the UI)
- `url`: The base URL of the MCP server (e.g., "https://mcp.example.com")
- `api_key`: Optional API key for authentication

## Troubleshooting

### DNS Resolution Issues

If you encounter errors like "No address associated with hostname", check:
1. The server URL is correct
2. Your network can reach the server
3. DNS resolution is working properly

### Connection Timeouts

If connections are timing out:
1. Increase the CONNECTION_TIMEOUT value
2. Check if the server is under high load
3. Verify network connectivity

### Enable Debug Mode

For detailed logging, enable DEBUG_MODE in the function settings.

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.