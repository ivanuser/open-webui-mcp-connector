# MCP Connector for Open WebUI

This repository provides integration between Open WebUI and MCP (Model Context Protocol) servers, allowing you to connect to any MCP-compatible server directly from your Open WebUI interface.

## Features

- Connect to any OpenAI API-compatible MCP servers from Open WebUI
- Manage multiple MCP server configurations
- Test connectivity to servers
- Secure API key storage
- Support for streaming responses
- Easy-to-use interface through Open WebUI Functions

## Installation

### Method 1: Manual Installation

1. Download the Function files:
   - `mcp_pipe.py` - The main connector Pipe Function
   - `mcp_action.py` - The server management Action Function

2. In Open WebUI, go to **Admin > Settings > Functions**

3. Click "Import" and select the downloaded files

4. Enable the imported Functions

### Method 2: Direct Installation from GitHub

1. In Open WebUI, go to **Admin > Settings > Functions**

2. Click "New" and select "Import from URL"

3. Enter the URL of the Function files:
   - Pipe Function: `https://raw.githubusercontent.com/ivanuser/open-webui-mcp-connector/main/mcp_pipe.py`
   - Action Function: `https://raw.githubusercontent.com/ivanuser/open-webui-mcp-connector/main/mcp_action.py`

4. Enable the imported Functions

## Usage

### Setting Up MCP Servers

1. Enable the "MCP Server Manager" Action Function

2. In a chat with any model, use the following commands:

   - **Add a server**:
     ```
     /add_server name="My MCP Server" url="https://example.com/api" api_key="your-api-key" default_model="model-name"
     ```
   
   - **List all servers**:
     ```
     /list_servers
     ```
   
   - **Test a server connection**:
     ```
     /test_connection server_id="server-id-from-list"
     ```
   
   - **Get available models**:
     ```
     /get_models server_id="server-id"
     ```
   
   - **Update a server**:
     ```
     /update_server server_id="server-id" name="New Name" url="new-url" api_key="new-key"
     ```
   
   - **Delete a server**:
     ```
     /delete_server server_id="server-id"
     ```

### Using MCP Servers

1. Enable the "MCP Connector" Pipe Function in **Admin > Settings > Functions**

2. Configure the Pipe Function:
   - Find "MCP Connector" and click the gear icon
   - Set the `server_id` valve to the ID of your MCP server (from the list_servers command)
   - Set a `default_model` if desired
   - Configure `timeout_seconds` and `stream` options as needed
   - Save the configuration

3. The MCP Connector will now appear as a model in your model selection dropdown

4. Select the "MCP Connector" to start chatting using your MCP server

## Compatibility

This connector works with any server that implements the OpenAI API-compatible endpoints:

- `/v1/chat/completions` - Used for chat interactions
- `/v1/models` - Used for listing available models

## Configuration

### MCP Pipe Function Options

The MCP Connector Pipe Function supports the following configuration options:

- `server_id` - ID of the MCP server to use (obtained from the MCP Manager)
- `default_model` - Default model to use if not specified in the request
- `timeout_seconds` - Timeout for server requests (default: 30 seconds)
- `stream` - Whether to use streaming mode for responses (default: false)

### Server Configuration

Each MCP server has the following properties:

- `name` - A friendly name for the server
- `url` - The base URL of the MCP server API
- `api_key` - API key for authentication (if required)
- `default_model` - Default model to use for this server

## Troubleshooting

If you encounter issues:

1. Check that the server URL is correct and includes the protocol (http:// or https://)
2. Verify your API key is valid
3. Ensure the server supports the OpenAI-compatible chat completions endpoint
4. Test the connection using the `/test_connection` command
5. Check for error messages in the Open WebUI logs
6. If you see parsing errors during installation, make sure you're using the latest version from this repository

## Local Development

To develop and test locally:

1. Clone this repository:
   ```
   git clone https://github.com/ivanuser/open-webui-mcp-connector.git
   cd open-webui-mcp-connector
   ```

2. Make your changes to the Python files

3. Test your changes:
   - Copy the files to your Open WebUI installation or import them directly in Admin > Settings > Functions
   - Try out the functions and debug any issues

4. To contribute back:
   - Fork this repository
   - Make your changes
   - Submit a Pull Request

## License

MIT