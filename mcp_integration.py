#!/usr/bin/env python3
"""
MCP Integration Layer for Qwen3
Provides WebSocket and HTTP endpoints for MCP protocol
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from aiohttp import web
import weakref

from dotenv import load_dotenv
from mcp_server import MCPServer
from fine_tune import QwenFineTuner, Tool
from tool_implementations import ToolExecutor, TOOL_DEFINITIONS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPWebSocketHandler:
    """Handles WebSocket connections for MCP protocol"""
    
    def __init__(self, mcp_server: MCPServer, qwen_integration: 'QwenMCPIntegration'):
        self.mcp_server = mcp_server
        self.qwen_integration = qwen_integration
        self._websockets = weakref.WeakSet()
    
    async def handle_websocket(self, request):
        """Handle WebSocket connection"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._websockets.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        # Parse the request
                        request_data = json.loads(msg.data)
                        logger.info(f"Received request: {request_data.get('method', 'unknown')}")
                        
                        # Process through MCP server
                        response = await self.mcp_server.handle_request(request_data)
                        
                        # Send response
                        await ws.send_json(response)
                        
                    except json.JSONDecodeError as e:
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": "Parse error",
                                "data": str(e)
                            },
                            "id": None
                        }
                        await ws.send_json(error_response)
                    except Exception as e:
                        logger.error(f"Error processing request: {e}")
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": "Internal error",
                                "data": str(e)
                            },
                            "id": request_data.get("id") if 'request_data' in locals() else None
                        }
                        await ws.send_json(error_response)
                        
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self._websockets.discard(ws)
            return ws
    
    async def broadcast_notification(self, notification: Dict[str, Any]):
        """Broadcast notification to all connected clients"""
        if self._websockets:
            await asyncio.gather(
                *[ws.send_json(notification) for ws in self._websockets],
                return_exceptions=True
            )

class QwenMCPIntegration:
    """Integration layer between Qwen3 model and MCP server"""
    
    def __init__(self):
        self.qwen_fine_tuner = None
        self.tool_executor = ToolExecutor()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.is_initialized = False
        
    def initialize(self):
        """Initialize the Qwen integration"""
        if not self.openrouter_api_key:
            logger.warning("OpenRouter API key not found. Model calls will use mock responses.")
        
        try:
            self.qwen_fine_tuner = QwenFineTuner(self.openrouter_api_key)
            
            # Register all tools
            for tool_def in TOOL_DEFINITIONS:
                tool = Tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    parameters=tool_def["parameters"]
                )
                self.qwen_fine_tuner.add_tool(tool)
            
            self.is_initialized = True
            logger.info("Qwen integration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qwen integration: {e}")
            self.is_initialized = False
    
    async def create_message(self, messages: list, model_preferences: dict = None, max_tokens: int = 1000) -> Dict[str, Any]:
        """Create a message using the Qwen model"""
        if not self.is_initialized or not self.openrouter_api_key:
            # Return mock response if not initialized
            return self._create_mock_response(messages)
        
        try:
            # Extract the last user message
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", {})
                    if isinstance(content, dict):
                        user_message = content.get("text", "")
                    else:
                        user_message = str(content)
                    break
            
            # Call the Qwen model through OpenRouter
            response = self.qwen_fine_tuner.test_model_with_tools(user_message)
            
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                message = choice.get("message", {})
                
                # Check if tools were used
                if "tool_calls" in message:
                    tool_calls = message["tool_calls"]
                    tool_results = []
                    
                    # Execute tools
                    for call in tool_calls:
                        function_name = call["function"]["name"]
                        arguments = json.loads(call["function"]["arguments"])
                        result = self.tool_executor.execute(function_name, arguments)
                        tool_results.append(result)
                    
                    # Combine results
                    response_content = self._format_tool_results(tool_results)
                else:
                    response_content = message.get("content", "")
                
                return {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": response_content
                    },
                    "model": "qwen3-235b",
                    "stopReason": "endTurn"
                }
            else:
                raise Exception("No response from model")
                
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return self._create_mock_response(messages)
    
    def _create_mock_response(self, messages: list) -> Dict[str, Any]:
        """Create a mock response when the model is not available"""
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else str(content)
        
        # Simple pattern matching for mock responses
        response_text = "I understand your request"
        
        if "weather" in text.lower():
            response_text = "Based on the available data, the weather in the requested location is currently partly cloudy with moderate temperatures."
        elif "calculate" in text.lower():
            response_text = "I can help you with calculations. Please provide the mathematical expression you'd like me to evaluate."
        elif "code" in text.lower():
            response_text = "I can help you write code. Please specify the programming language and the task you'd like to accomplish."
        else:
            response_text = f"I received your message: '{text[:50]}...'. How can I help you with this?"
        
        return {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": response_text
            },
            "model": "qwen3-235b-mock",
            "stopReason": "endTurn"
        }
    
    def _format_tool_results(self, tool_results: list) -> str:
        """Format tool results into a readable response"""
        formatted_parts = []
        
        for result in tool_results:
            if result["status"] == "success":
                result_data = result["result"]
                if isinstance(result_data, dict):
                    formatted_parts.append(json.dumps(result_data, indent=2))
                else:
                    formatted_parts.append(str(result_data))
            else:
                formatted_parts.append(f"Error: {result['error']}")
        
        return "\n\n".join(formatted_parts)

class MCPApplication:
    """Main application combining MCP server with HTTP/WebSocket endpoints"""
    
    def __init__(self):
        self.mcp_server = MCPServer()
        self.qwen_integration = QwenMCPIntegration()
        self.ws_handler = MCPWebSocketHandler(self.mcp_server, self.qwen_integration)
        self.app = web.Application()
        self._setup_routes()
        
        # Inject Qwen integration into MCP server
        self._inject_qwen_integration()
    
    def _inject_qwen_integration(self):
        """Inject Qwen integration into MCP server"""
        # Override the sampling handler to use real model
        async def enhanced_sampling_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            messages = params.get("messages", [])
            model_preferences = params.get("modelPreferences", {})
            max_tokens = params.get("maxTokens", 1000)
            
            return await self.qwen_integration.create_message(
                messages, model_preferences, max_tokens
            )
        
        self.mcp_server.handle_sampling_create_message = enhanced_sampling_handler
    
    def _setup_routes(self):
        """Setup HTTP and WebSocket routes"""
        # WebSocket endpoint for MCP protocol
        self.app.router.add_get('/mcp', self.ws_handler.handle_websocket)
        
        # HTTP endpoints
        self.app.router.add_post('/api/v1/messages', self.handle_http_message)
        self.app.router.add_get('/api/v1/health', self.handle_health)
        self.app.router.add_get('/api/v1/info', self.handle_info)
        
        # Static files (if needed)
        self.app.router.add_get('/', self.handle_index)
    
    async def handle_http_message(self, request):
        """Handle HTTP message creation request"""
        try:
            data = await request.json()
            messages = data.get("messages", [])
            
            result = await self.qwen_integration.create_message(messages)
            
            return web.json_response({
                "success": True,
                "message": result
            })
        except Exception as e:
            logger.error(f"HTTP message error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "initialized": self.qwen_integration.is_initialized
        })
    
    async def handle_info(self, request):
        """Server information endpoint"""
        return web.json_response({
            "server": self.mcp_server.server_info,
            "tools": [tool["name"] for tool in TOOL_DEFINITIONS],
            "model": {
                "name": "qwen3-235b",
                "provider": "openrouter",
                "initialized": self.qwen_integration.is_initialized
            }
        })
    
    async def handle_index(self, request):
        """Serve a simple index page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Qwen3 MCP Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .info { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                code { background-color: #e0e0e0; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>Qwen3 Model Context Protocol Server</h1>
            <div class="info">
                <h2>Endpoints:</h2>
                <ul>
                    <li><strong>WebSocket MCP:</strong> <code>ws://localhost:8080/mcp</code></li>
                    <li><strong>HTTP API:</strong> <code>POST /api/v1/messages</code></li>
                    <li><strong>Health Check:</strong> <code>GET /api/v1/health</code></li>
                    <li><strong>Server Info:</strong> <code>GET /api/v1/info</code></li>
                </ul>
                <h2>MCP Protocol Version:</h2>
                <p>2025-06-18</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def start(self, host='0.0.0.0', port=8080):
        """Start the application"""
        # Initialize Qwen integration
        self.qwen_integration.initialize()
        
        # Setup application
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        
        logger.info(f"Starting MCP server on {host}:{port}")
        await site.start()
        
        # Keep the server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            await runner.cleanup()

async def main():
    """Main entry point"""
    app = MCPApplication()
    await app.start()

if __name__ == "__main__":
    asyncio.run(main())
