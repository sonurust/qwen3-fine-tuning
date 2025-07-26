#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Server Implementation for Qwen3
Following MCP Specification 2025-06-18
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from tool_implementations import ToolExecutor, TOOL_DEFINITIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
MCP_VERSION = "2025-06-18"
JSONRPC_VERSION = "2.0"

@dataclass
class MCPError:
    """MCP Error structure"""
    code: int
    message: str
    data: Optional[Any] = None

    # Standard error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

@dataclass
class MCPRequest:
    """MCP Request structure"""
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

@dataclass
class MCPResponse:
    """MCP Response structure"""
    jsonrpc: str = JSONRPC_VERSION
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

@dataclass
class MCPNotification:
    """MCP Notification structure"""
    method: str
    jsonrpc: str = JSONRPC_VERSION
    params: Optional[Dict[str, Any]] = None

class MCPServer:
    """
    Model Context Protocol Server Implementation
    Provides tools, resources, and prompts for the Qwen3 model
    """
    
    def __init__(self):
        self.tool_executor = ToolExecutor()
        self.server_info = {
            "name": "qwen3-mcp-server",
            "version": "1.0.0",
            "protocolVersion": MCP_VERSION,
            "capabilities": {
                "tools": {
                    "supported": True
                },
                "prompts": {
                    "supported": True
                },
                "resources": {
                    "supported": True,
                    "subscriptions": True
                },
                "sampling": {
                    "supported": True
                }
            }
        }
        self.sessions = {}
        self.resources = {}
        self.prompts = self._initialize_prompts()
        
    def _initialize_prompts(self) -> Dict[str, Any]:
        """Initialize available prompts"""
        return {
            "weather_check": {
                "name": "weather_check",
                "description": "Check weather for a location",
                "arguments": {
                    "location": {
                        "type": "string",
                        "description": "City and state/country",
                        "required": True
                    }
                }
            },
            "code_generation": {
                "name": "code_generation",
                "description": "Generate code based on requirements",
                "arguments": {
                    "language": {
                        "type": "string",
                        "description": "Programming language",
                        "required": True
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description",
                        "required": True
                    }
                }
            },
            "calculation": {
                "name": "calculation",
                "description": "Perform mathematical calculations",
                "arguments": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression",
                        "required": True
                    }
                }
            }
        }
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        try:
            # Parse request
            request = MCPRequest(**request_data)
            
            # Validate JSON-RPC version
            if request.jsonrpc != JSONRPC_VERSION:
                return self._error_response(
                    MCPError.INVALID_REQUEST,
                    "Invalid JSON-RPC version",
                    request.id
                )
            
            # Route to appropriate handler
            method_handlers = {
                # Base protocol methods
                "initialize": self.handle_initialize,
                "ping": self.handle_ping,
                "shutdown": self.handle_shutdown,
                
                # Tool methods
                "tools/list": self.handle_tools_list,
                "tools/call": self.handle_tools_call,
                
                # Prompt methods
                "prompts/list": self.handle_prompts_list,
                "prompts/get": self.handle_prompts_get,
                
                # Resource methods
                "resources/list": self.handle_resources_list,
                "resources/read": self.handle_resources_read,
                "resources/subscribe": self.handle_resources_subscribe,
                "resources/unsubscribe": self.handle_resources_unsubscribe,
                
                # Sampling methods
                "sampling/createMessage": self.handle_sampling_create_message,
                
                # Completion methods
                "completion/complete": self.handle_completion_complete,
            }
            
            handler = method_handlers.get(request.method)
            if not handler:
                return self._error_response(
                    MCPError.METHOD_NOT_FOUND,
                    f"Method '{request.method}' not found",
                    request.id
                )
            
            # Execute handler
            result = await handler(request.params or {})
            
            # Return response
            return asdict(MCPResponse(
                id=request.id,
                result=result
            ))
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._error_response(
                MCPError.INTERNAL_ERROR,
                str(e),
                request_data.get("id")
            )
    
    def _error_response(self, code: int, message: str, request_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
        """Create error response"""
        return asdict(MCPResponse(
            id=request_id,
            error={
                "code": code,
                "message": message
            }
        ))
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        client_info = params.get("clientInfo", {})
        
        # Create session
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "clientInfo": client_info,
            "createdAt": datetime.utcnow().isoformat(),
            "subscriptions": []
        }
        
        return {
            "serverInfo": self.server_info,
            "sessionId": session_id,
            "instructions": "Qwen3 MCP Server ready. Use tools for weather, calculations, code execution, and more."
        }
    
    async def handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request"""
        return {"pong": True}
    
    async def handle_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shutdown request"""
        # Clean up sessions
        self.sessions.clear()
        return {"success": True}
    
    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        tools = []
        for tool_def in TOOL_DEFINITIONS:
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "inputSchema": tool_def["parameters"]
            })
        
        return {
            "tools": tools,
            "_meta": {
                "total": len(tools)
            }
        }
    
    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        # Execute tool
        result = self.tool_executor.execute(tool_name, arguments)
        
        # Format response based on tool result
        if result["status"] == "success":
            return {
                "toolResult": result["result"],
                "isError": False
            }
        else:
            return {
                "toolResult": result["error"],
                "isError": True
            }
    
    async def handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available prompts"""
        prompts = []
        for prompt_id, prompt_data in self.prompts.items():
            prompts.append({
                "name": prompt_data["name"],
                "description": prompt_data["description"],
                "arguments": list(prompt_data["arguments"].keys())
            })
        
        return {
            "prompts": prompts,
            "_meta": {
                "total": len(prompts)
            }
        }
    
    async def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific prompt"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        prompt = self.prompts[prompt_name]
        
        # Generate prompt based on type
        if prompt_name == "weather_check":
            location = arguments.get("location", "Unknown")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"What's the weather like in {location}?"
                    }
                }
            ]
        elif prompt_name == "code_generation":
            language = arguments.get("language", "Python")
            task = arguments.get("task", "")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Write {language} code to {task}"
                    }
                }
            ]
        elif prompt_name == "calculation":
            expression = arguments.get("expression", "")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Calculate: {expression}"
                    }
                }
            ]
        else:
            messages = []
        
        return {
            "description": prompt["description"],
            "messages": messages
        }
    
    async def handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources"""
        resources = [
            {
                "uri": "mcp://qwen3/training-data",
                "name": "Training Data",
                "mimeType": "application/json",
                "description": "Fine-tuning training data"
            },
            {
                "uri": "mcp://qwen3/config",
                "name": "Configuration",
                "mimeType": "application/json",
                "description": "Model configuration"
            },
            {
                "uri": "mcp://qwen3/prompt-template",
                "name": "Prompt Template",
                "mimeType": "text/plain",
                "description": "Custom prompt template"
            }
        ]
        
        return {
            "resources": resources,
            "_meta": {
                "total": len(resources)
            }
        }
    
    async def handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a resource"""
        uri = params.get("uri")
        
        if uri == "mcp://qwen3/training-data":
            # Read training data
            try:
                with open("training_data.jsonl", "r") as f:
                    contents = []
                    for line in f:
                        contents.append(json.loads(line.strip()))
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(contents, indent=2)
                        }
                    ]
                }
            except FileNotFoundError:
                raise ValueError("Training data not found")
                
        elif uri == "mcp://qwen3/config":
            # Read config
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(config, indent=2)
                        }
                    ]
                }
            except FileNotFoundError:
                raise ValueError("Configuration not found")
                
        elif uri == "mcp://qwen3/prompt-template":
            # Read prompt template
            try:
                with open("prompt_template.txt", "r") as f:
                    template = f.read()
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/plain",
                            "text": template
                        }
                    ]
                }
            except FileNotFoundError:
                raise ValueError("Prompt template not found")
        
        else:
            raise ValueError(f"Resource '{uri}' not found")
    
    async def handle_resources_subscribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Subscribe to resource updates"""
        uri = params.get("uri")
        session_id = params.get("sessionId")
        
        if session_id in self.sessions:
            self.sessions[session_id]["subscriptions"].append(uri)
        
        return {"success": True}
    
    async def handle_resources_unsubscribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Unsubscribe from resource updates"""
        uri = params.get("uri")
        session_id = params.get("sessionId")
        
        if session_id in self.sessions:
            subscriptions = self.sessions[session_id]["subscriptions"]
            if uri in subscriptions:
                subscriptions.remove(uri)
        
        return {"success": True}
    
    async def handle_sampling_create_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a message using the model"""
        messages = params.get("messages", [])
        model_preferences = params.get("modelPreferences", {})
        include_context = params.get("includeContext", "none")
        max_tokens = params.get("maxTokens", 1000)
        
        # This would integrate with the actual Qwen model
        # For now, return a mock response
        response_content = "This is a sample response from the Qwen3 model."
        
        # If there are tool calls needed based on the message
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", {}).get("text", "")
        
        # Simple pattern matching for tool usage
        tool_response = None
        if "weather" in content.lower():
            tool_response = {
                "name": "get_weather",
                "arguments": {"location": "San Francisco, CA"}
            }
        elif "calculate" in content.lower():
            tool_response = {
                "name": "calculate",
                "arguments": {"expression": "2+2"}
            }
        
        return {
            "role": "assistant",
            "content": {
                "type": "text",
                "text": response_content
            },
            "model": "qwen3-235b",
            "stopReason": "endTurn"
        }
    
    async def handle_completion_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completion request"""
        ref = params.get("ref")
        argument = params.get("argument", {})
        
        # Simple completion based on argument name
        completions = []
        
        if argument.get("name") == "location":
            completions = [
                {"value": "San Francisco, CA"},
                {"value": "New York, NY"},
                {"value": "London, UK"},
                {"value": "Tokyo, Japan"}
            ]
        elif argument.get("name") == "language":
            completions = [
                {"value": "Python"},
                {"value": "JavaScript"},
                {"value": "Go"},
                {"value": "Rust"}
            ]
        
        return {
            "completion": {
                "values": completions,
                "hasMore": False
            }
        }
    
    async def notify_resource_update(self, uri: str, update_type: str = "updated"):
        """Send resource update notification to subscribed clients"""
        notification = MCPNotification(
            method="notifications/resources/update",
            params={
                "uri": uri,
                "updateType": update_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # In a real implementation, this would send to connected clients
        logger.info(f"Resource update notification: {uri} - {update_type}")

async def main():
    """Main entry point for testing"""
    server = MCPServer()
    
    # Test initialize
    init_response = await server.handle_request({
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    })
    print("Initialize response:", json.dumps(init_response, indent=2))
    
    # Test tools list
    tools_response = await server.handle_request({
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    })
    print("\nTools list response:", json.dumps(tools_response, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
