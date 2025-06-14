# StreamableHTTP-MCP-boilerplate

A boilerplate implementation of a Model Context Protocol (MCP) server with **Streamable HTTP** transport for VS Code Copilot integration. This template provides a foundation for building custom MCP servers that can seamlessly integrate with AI coding assistants.

## 🚀 Features

- **Streamable HTTP Transport**: Uses NDJSON (newline-delimited JSON) for real-time streaming communication
- **VS Code Copilot Ready**: Configured for seamless integration with VS Code Copilot
- **Dual Mode Support**: Can run as HTTP server or traditional stdio MCP server
- **Example Tools Included**: Time and weather tools as implementation examples
- **Production Ready**: Includes proper error handling, CORS support, and health checks
- **Modern Python**: Built with async/await, type hints, and modern Python practices

## 📋 Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip for dependency management

## 🛠️ Installation

### Using uv (Recommended)

```bash
git clone https://github.com/yourusername/StreamableHTTP-MCP-boilerplate.git
cd StreamableHTTP-MCP-boilerplate
uv sync
```

### Using pip

```bash
git clone https://github.com/yourusername/StreamableHTTP-MCP-boilerplate.git
cd StreamableHTTP-MCP-boilerplate
pip install -r requirements.txt
```

## ⚙️ Configuration

### Environment Variables

For the weather tool example, you'll need a free API key:

```bash
# Create a .env file in the project root
echo "WEATHER_API_KEY=your_weather_api_key_here" > .env
# Get a free API key from https://www.weatherapi.com/
```

### VS Code Copilot Integration

Add this configuration to your VS Code settings or MCP client:

```json
{
  "mcp": {
    "servers": {
      "your-custom-server": {
        "url": "http://localhost:8000"
      }
    }
  }
}
```

## 🏃‍♂️ Running the Server

### HTTP Mode (for VS Code Copilot)

```bash
# Using uv
uv run main.py --http

# Using python directly
python main.py --http
```

Server will start on `http://localhost:8000` with endpoints:
- **Main MCP endpoint**: `http://localhost:8000/mcp` (POST)
- **Alternative endpoint**: `http://localhost:8000/` (POST)
- **Health check**: `http://localhost:8000/health` (GET)

### STDIO Mode (traditional MCP)

```bash
# Using uv
uv run main.py

# Using python directly
python main.py
```

## 🧪 Testing

### Health Check

```bash
curl http://localhost:8000/health
```

### List Available Tools

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### Test Time Tool

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "time_tool",
      "arguments": {"input_timezone": "Asia/Kolkata"}
    }
  }'
```

### Test Weather Tool

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "weather_tool",
      "arguments": {"location": "Mumbai"}
    }
  }'
```

## 📚 Implementation Details

### Architecture Overview

This MCP server implements the [Model Context Protocol](https://spec.modelcontextprotocol.io/) specification with a custom Streamable HTTP transport layer. The architecture consists of:

1. **MCP Server Core**: Handles protocol compliance and tool registration
2. **Streamable HTTP Transport**: Custom transport layer using Starlette and NDJSON
3. **Tool Implementation**: Example tools (time and weather) with proper async handling
4. **Error Handling**: Comprehensive error handling following JSON-RPC 2.0 standards

### Key Components

#### MCP Protocol Handler

The server implements these core MCP methods:

- `initialize`: Server initialization and capability negotiation
- `tools/list`: Returns available tools with their schemas
- `tools/call`: Executes tools with provided arguments

#### Streamable HTTP Transport

Uses **NDJSON** (Newline-Delimited JSON) format for streaming:

```python
async def stream_generator(request_body: bytes):
    # Parse incoming JSON-RPC message
    # Process through MCP protocol
    # Stream response as NDJSON
    yield json.dumps(response) + "\n"
```

#### Response Format

All responses follow JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tool execution result"
      }
    ]
  }
}
```

### Why Streamable HTTP?

Traditional MCP implementations use stdio transport, which works well for command-line tools but has limitations for web-based integrations. Streamable HTTP provides:

- **Real-time Communication**: Immediate response streaming
- **Web Compatibility**: Works with any HTTP client
- **Scalability**: Can handle multiple concurrent connections
- **Debugging**: Easy to test with standard HTTP tools

## 🔧 Customization Guide

### Adding New Tools

1. **Define your tool function**:

```python
async def your_custom_tool(param1: str, param2: int = 10) -> List[types.TextContent]:
    """Your custom tool description."""
    try:
        # Your tool logic here
        result = f"Processed {param1} with value {param2}"
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]
```

2. **Register in the tools list**:

```python
@server.list_tools()
async def list_tools() -> List[types.Tool]:
    return [
        # ... existing tools
        types.Tool(
            name="your_custom_tool",
            description="Description of what your tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of param1"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "Description of param2",
                        "default": 10
                    }
                },
                "required": ["param1"],
                "additionalProperties": False
            }
        )
    ]
```

3. **Add to the call handler**:

```python
@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    if name == "your_custom_tool":
        return await your_custom_tool(
            arguments.get("param1"),
            arguments.get("param2", 10)
        )
    # ... existing tool handlers
```

### Customizing the Server

- **Change server info**: Update the server name and version in the `initialize` response
- **Add middleware**: Use Starlette middleware for authentication, logging, etc.
- **Custom endpoints**: Add additional HTTP endpoints for webhooks or health checks
- **Environment config**: Add configuration management for different environments

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure dependencies are installed
   uv sync
   # or
   pip install -r requirements.txt
   ```

2. **VS Code Connection Issues**
   - Ensure server is running on the correct port
   - Check VS Code configuration matches server URL
   - Verify `/mcp` endpoint is accessible

3. **Weather API Errors**
   - Verify `WEATHER_API_KEY` environment variable is set
   - Check API key is valid at [WeatherAPI.com](https://www.weatherapi.com/)

4. **Timezone Errors**
   - Use standard timezone identifiers (e.g., "Asia/Kolkata", not "IST")
   - Refer to [IANA timezone database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

5. **Port Conflicts**
   ```bash
   # Change port using environment variable
   PORT=8080 uv run main.py --http
   ```

### Debug Mode

Enable debug logging by setting the log level in uvicorn config:

```python
config = uvicorn.Config(
    app=app,
    host="0.0.0.0", 
    port=port,
    log_level="debug"  # Change from "info" to "debug"
)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add some feature'`
5. Push to the branch: `git push origin feature/your-feature`
6. Submit a pull request

## 📝 Example Tools Included

### Time Tool
- **Purpose**: Get current time for any timezone
- **Parameters**: `input_timezone` (optional) - IANA timezone identifier
- **Example**: Get time in Tokyo: `{"input_timezone": "Asia/Tokyo"}`

### Weather Tool  
- **Purpose**: Get current weather for any location
- **Parameters**: `location` (required) - City, coordinates, or location string
- **Example**: Weather in London: `{"location": "London"}`
- **Requires**: Free API key from [WeatherAPI.com](https://www.weatherapi.com/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://spec.modelcontextprotocol.io/) specification
- [Anthropic MCP](https://github.com/modelcontextprotocol) for the Python implementation
- [Starlette](https://www.starlette.io/) for the excellent ASGI framework

---

## 🔗 Related Links

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [VS Code Copilot Documentation](https://code.visualstudio.com/docs/editor/artificial-intelligence)
- [Starlette Documentation](https://www.starlette.io/)
- [uv Package Manager](https://github.com/astral-sh/uv)

---

**Made with ❤️ for the MCP community**