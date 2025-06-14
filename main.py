#!/usr/bin/env python3
"""
MCP Server with Streamable HTTP Transport for IDEs
Provides tools via streamable HTTP interface.
"""

import asyncio
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from starlette.routing import Route
import uvicorn
from dotenv import load_dotenv


# Initialize MCP Server
server = Server("time-weather-mcp")


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="time_tool",
            description="Get current time for a timezone (e.g. Asia/Kolkata)",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_timezone": {
                        "type": "string",
                        "description": "Timezone identifier (e.g., 'Asia/Kolkata', 'America/New_York'). Optional, defaults to system timezone."
                    }
                },
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="weather_tool", 
            description="Provides weather info for a given location",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location to get weather for (city name, coordinates, etc.)"
                    }
                },
                "required": ["location"],
                "additionalProperties": False
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""
    
    if name == "time_tool":
        return await time_tool(arguments.get("input_timezone"))
    elif name == "weather_tool":
        return await weather_tool(arguments.get("location"))
    else:
        raise ValueError(f"Unknown tool: {name}")


async def time_tool(input_timezone: Optional[str] = None) -> List[types.TextContent]:
    """Get current time for a timezone (e.g. Asia/Kolkata)."""
    try:
        fmt = "%Y-%m-%d %H:%M:%S %Z%z"
        now = datetime.datetime.now()
        
        if input_timezone:
            try:
                now = now.astimezone(ZoneInfo(input_timezone))
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Invalid timezone '{input_timezone}'. Error: {str(e)}"
                )]
        
        result = f"The current time is {now.strftime(fmt)}."
        return [types.TextContent(type="text", text=result)]
    
    except Exception as e:
        return [types.TextContent(
            type="text", 
            text=f"Error getting time: {str(e)}"
        )]


async def weather_tool(location: str) -> List[types.TextContent]:
    """Provides weather info for a given location."""
    if not location:
        return [types.TextContent(
            type="text",
            text="Location parameter is required."
        )]
    
    try:
        load_dotenv()
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            return [types.TextContent(
                type="text",
                text="Weather API key not found. Please set WEATHER_API_KEY environment variable."
            )]
        
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi=no"
        print(url)
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        data = resp.json().get("current")
        if not data:
            return [types.TextContent(
                type="text",
                text=f"Sorry, couldn't find weather for {location}."
            )]
        
        result = f"The weather in {location} is {data['condition']['text']} at {data['temp_c']}°C."
        return [types.TextContent(type="text", text=result)]
    
    except requests.RequestException as e:
        return [types.TextContent(
            type="text",
            text=f"Error fetching weather data: {str(e)}"
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting weather: {str(e)}"
        )]


# Streamable HTTP Transport
class StreamableHttpTransport:
    """Custom streamable HTTP transport for MCP."""
    
    def __init__(self):
        self.read_stream = None
        self.write_stream = None
    
    async def read_message(self) -> Optional[Dict[str, Any]]:
        """Read a message from the stream."""
        if self.read_stream:
            try:
                line = await self.read_stream.readline()
                if line:
                    return json.loads(line.decode().strip())
            except Exception:
                pass
        return None
    
    async def write_message(self, message: Dict[str, Any]) -> None:
        """Write a message to the stream."""
        if self.write_stream:
            try:
                data = json.dumps(message) + "\n"
                self.write_stream.write(data.encode())
                await self.write_stream.drain()
            except Exception:
                pass


async def stream_generator(request_body: bytes):
    """Generate streaming response for MCP communication."""
    try:
        # Parse the incoming request
        message = json.loads(request_body.decode())
        
        # Handle different MCP methods
        if message.get("method") == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "time-weather-mcp",
                        "version": "1.0.0"
                    }
                }
            }
            yield json.dumps(response) + "\n"
        
        elif message.get("method") == "tools/list":
            tools = await list_tools()
            tools_dict = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": tools_dict
                }
            }
            yield json.dumps(response) + "\n"
        
        elif message.get("method") == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                result = await call_tool(tool_name, arguments)
                content = [{"type": content.type, "text": content.text} for content in result]
                
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "content": content
                    }
                }
                yield json.dumps(response) + "\n"
            
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    }
                }
                yield json.dumps(error_response) + "\n"
        
        else:
            # Unknown method
            error_response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {message.get('method')}"
                }
            }
            yield json.dumps(error_response) + "\n"
    
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": f"Parse error: {str(e)}"
            }
        }
        yield json.dumps(error_response) + "\n"


async def handle_stream(request):
    """Handle streamable HTTP requests."""
    if request.method == "POST":
        try:
            body = await request.body()
            
            return StreamingResponse(
                stream_generator(body),
                media_type="application/x-ndjson",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
            return StreamingResponse(
                iter([json.dumps(error_response) + "\n"]),
                media_type="application/x-ndjson",
                status_code=500
            )
    
    # Method not allowed
    error_response = {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": -32000,
            "message": "Method not allowed"
        }
    }
    return StreamingResponse(
        iter([json.dumps(error_response) + "\n"]),
        media_type="application/x-ndjson",
        status_code=405
    )


async def handle_health(request):
    """Health check endpoint."""
    return StreamingResponse(
        iter([json.dumps({"status": "healthy"}) + "\n"]),
        media_type="application/json"
    )


# Starlette app setup
app = Starlette(
    routes=[
        Route("/", handle_stream, methods=["POST"]),
        Route("/mcp", handle_stream, methods=["POST"]),  # VS Code Copilot expects this endpoint
        Route("/health", handle_health, methods=["GET"]),
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def main():
    """Main entry point - can run as stdio or HTTP server."""
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        # Run HTTP server
        port = int(os.getenv("PORT", "8000"))
        print(f"Starting MCP Streamable HTTP server on port {port}")
        print(f"Endpoint: http://localhost:{port}/")
        print(f"Health check: http://localhost:{port}/health")
        
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        server_instance = uvicorn.Server(config)
        await server_instance.serve()
    else:
        # Run stdio server (default)
        print("Starting MCP stdio server")
        async with stdio_server() as streams:
            await server.run(
                streams[0], 
                streams[1], 
                initialization_options={}
            )


if __name__ == "__main__":
    asyncio.run(main())