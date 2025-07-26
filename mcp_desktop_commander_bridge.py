#!/usr/bin/env python3
"""
MCP Bridge for integrating DesktopCommanderMCP with Qwen3 MCP Server
This allows the Qwen3 model to use DesktopCommander's enhanced capabilities
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DesktopCommanderBridge:
    """
    Bridge to connect DesktopCommanderMCP capabilities with Qwen3 MCP Server
    """
    
    def __init__(self, desktop_commander_url: str = "http://desktop-commander:3000"):
        self.desktop_commander_url = desktop_commander_url
        self.session = None
        
    async def initialize(self):
        """Initialize the bridge connection"""
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        """Close the bridge connection"""
        if self.session:
            await self.session.close()
    
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute a terminal command through DesktopCommander"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "execute_command",
                "params": {
                    "command": command,
                    "timeout": timeout or 30
                },
                "id": f"cmd_{datetime.utcnow().timestamp()}"
            }
            
            async with self.session.post(
                f"{self.desktop_commander_url}/rpc",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout + 10 if timeout else 40)
            ) as response:
                result = await response.json()
                
                if "error" in result:
                    return {
                        "status": "error",
                        "error": result["error"]["message"],
                        "code": result["error"]["code"]
                    }
                
                return {
                    "status": "success",
                    "output": result.get("result", {}).get("output", ""),
                    "exit_code": result.get("result", {}).get("exitCode", 0)
                }
                
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": "Command execution timed out"
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def search_files(self, query: str, path: str = ".", max_results: int = 50) -> Dict[str, Any]:
        """Search files using DesktopCommander's ripgrep integration"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "search_code",
                "params": {
                    "query": query,
                    "path": path,
                    "maxResults": max_results
                },
                "id": f"search_{datetime.utcnow().timestamp()}"
            }
            
            async with self.session.post(
                f"{self.desktop_commander_url}/rpc",
                json=payload
            ) as response:
                result = await response.json()
                
                if "error" in result:
                    return {
                        "status": "error",
                        "error": result["error"]["message"]
                    }
                
                return {
                    "status": "success",
                    "results": result.get("result", {}).get("results", [])
                }
                
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def edit_file(self, file_path: str, edits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Edit files using DesktopCommander's advanced editing capabilities"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "edit_files",
                "params": {
                    "edits": [{
                        "filePath": file_path,
                        "edits": edits
                    }]
                },
                "id": f"edit_{datetime.utcnow().timestamp()}"
            }
            
            async with self.session.post(
                f"{self.desktop_commander_url}/rpc",
                json=payload
            ) as response:
                result = await response.json()
                
                if "error" in result:
                    return {
                        "status": "error",
                        "error": result["error"]["message"]
                    }
                
                return {
                    "status": "success",
                    "result": result.get("result", {})
                }
                
        except Exception as e:
            logger.error(f"Error editing file: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def manage_process(self, action: str, process_id: Optional[int] = None) -> Dict[str, Any]:
        """Manage processes through DesktopCommander"""
        try:
            params = {"action": action}
            if process_id:
                params["processId"] = process_id
            
            payload = {
                "jsonrpc": "2.0",
                "method": "manage_process",
                "params": params,
                "id": f"process_{datetime.utcnow().timestamp()}"
            }
            
            async with self.session.post(
                f"{self.desktop_commander_url}/rpc",
                json=payload
            ) as response:
                result = await response.json()
                
                if "error" in result:
                    return {
                        "status": "error",
                        "error": result["error"]["message"]
                    }
                
                return {
                    "status": "success",
                    "result": result.get("result", {})
                }
                
        except Exception as e:
            logger.error(f"Error managing process: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# Enhanced tool definitions for DesktopCommander integration
DESKTOP_COMMANDER_TOOLS = [
    {
        "name": "execute_terminal_command",
        "description": "Execute terminal commands with enhanced capabilities (streaming, timeout, background)",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The terminal command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30
                },
                "background": {
                    "type": "boolean",
                    "description": "Run command in background",
                    "default": False
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "search_code",
        "description": "Search for code or text in files using ripgrep",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (regex supported)"
                },
                "path": {
                    "type": "string",
                    "description": "Directory path to search in",
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to filter (e.g., '*.py')"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Case sensitive search",
                    "default": False
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "advanced_file_edit",
        "description": "Edit files with surgical precision using block replacements",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "edits": {
                    "type": "array",
                    "description": "List of edit operations",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["replace", "insert", "delete"],
                                "description": "Type of edit operation"
                            },
                            "search": {
                                "type": "string",
                                "description": "Text to search for (for replace operations)"
                            },
                            "replace": {
                                "type": "string",
                                "description": "Text to replace with"
                            },
                            "line": {
                                "type": "integer",
                                "description": "Line number for insert/delete operations"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to insert"
                            }
                        }
                    }
                }
            },
            "required": ["file_path", "edits"]
        }
    },
    {
        "name": "manage_processes",
        "description": "List and manage running processes",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "kill", "info"],
                    "description": "Action to perform"
                },
                "process_id": {
                    "type": "integer",
                    "description": "Process ID (for kill/info actions)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "execute_code_in_memory",
        "description": "Execute code in memory without saving files (Python, Node.js, R)",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "node", "r"],
                    "description": "Programming language"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30
                }
            },
            "required": ["code", "language"]
        }
    }
]

async def integrate_desktop_commander_tools(mcp_server):
    """
    Integrate DesktopCommander tools into the existing MCP server
    """
    bridge = DesktopCommanderBridge()
    await bridge.initialize()
    
    # Register enhanced tools
    for tool_def in DESKTOP_COMMANDER_TOOLS:
        logger.info(f"Registering DesktopCommander tool: {tool_def['name']}")
        # Add tool to MCP server's tool registry
        # This would be integrated with the existing tool system
    
    return bridge
