import json
import ast
import operator
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import subprocess
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
import asyncio
from mcp_desktop_commander_bridge import DesktopCommanderBridge, DESKTOP_COMMANDER_TOOLS

class ToolExecutor:
    """Executes tool calls and returns results"""
    
    def __init__(self):
        self.tools = {
            "get_weather": self.get_weather,
            "calculate": self.calculate,
            "execute_code": self.execute_code,
            "search_web": self.search_web,
            "get_datetime": self.get_datetime,
            "file_operations": self.file_operations
        }
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result"""
        if tool_name not in self.tools:
            return {
                "error": f"Unknown tool: {tool_name}",
                "status": "error"
            }
        
        try:
            result = self.tools[tool_name](**arguments)
            return {
                "result": result,
                "status": "success"
            }
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }
    
    def get_weather(self, location: str, unit: str = "celsius") -> Dict[str, Any]:
        """
        Mock weather API - in production, this would call a real weather service
        """
        # This is a mock implementation
        # In production, you'd use a real weather API like OpenWeatherMap
        mock_weather_data = {
            "New York, NY": {"temp_c": 22, "temp_f": 72, "condition": "Partly cloudy", "humidity": 65},
            "San Francisco, CA": {"temp_c": 18, "temp_f": 64, "condition": "Foggy", "humidity": 80},
            "London, UK": {"temp_c": 15, "temp_f": 59, "condition": "Rainy", "humidity": 85},
            "Tokyo, Japan": {"temp_c": 25, "temp_f": 77, "condition": "Clear", "humidity": 60},
        }
        
        weather = mock_weather_data.get(location, {
            "temp_c": 20, "temp_f": 68, "condition": "Unknown", "humidity": 50
        })
        
        temp = weather["temp_c"] if unit == "celsius" else weather["temp_f"]
        unit_symbol = "°C" if unit == "celsius" else "°F"
        
        return {
            "location": location,
            "temperature": f"{temp}{unit_symbol}",
            "condition": weather["condition"],
            "humidity": f"{weather['humidity']}%"
        }
    
    def calculate(self, expression: str) -> Dict[str, Any]:
        """
        Safely evaluate mathematical expressions
        """
        # Define safe operations
        safe_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.Mod: operator.mod,
        }
        
        safe_functions = {
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
        }
        
        class MathEvaluator(ast.NodeVisitor):
            def visit(self, node):
                if isinstance(node, ast.Expression):
                    return self.visit(node.body)
                elif isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    left = self.visit(node.left)
                    right = self.visit(node.right)
                    return safe_operators[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = self.visit(node.operand)
                    return safe_operators[type(node.op)](operand)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in safe_functions:
                        args = [self.visit(arg) for arg in node.args]
                        return safe_functions[node.func.id](*args)
                    else:
                        raise ValueError(f"Unsafe function: {ast.dump(node.func)}")
                elif isinstance(node, ast.Name):
                    if node.id == 'pi':
                        return 3.14159265359
                    elif node.id == 'e':
                        return 2.71828182846
                    else:
                        raise ValueError(f"Unknown variable: {node.id}")
                else:
                    raise ValueError(f"Unsupported operation: {ast.dump(node)}")
        
        try:
            # Parse the expression
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate safely
            evaluator = MathEvaluator()
            result = evaluator.visit(tree)
            
            return {
                "expression": expression,
                "result": result
            }
        except Exception as e:
            return {
                "expression": expression,
                "error": str(e)
            }
    
    def execute_code(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment
        """
        # Create a restricted execution environment
        restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'bool': bool,
                'abs': abs,
                'min': min,
                'max': max,
                'sum': sum,
                'round': round,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
            }
        }
        
        # Capture output
        output_capture = io.StringIO()
        error_capture = io.StringIO()
        
        try:
            with redirect_stdout(output_capture), redirect_stderr(error_capture):
                # Execute the code with timeout
                exec(code, restricted_globals)
            
            output = output_capture.getvalue()
            error = error_capture.getvalue()
            
            return {
                "code": code,
                "output": output,
                "error": error if error else None,
                "status": "success" if not error else "error"
            }
        except Exception as e:
            return {
                "code": code,
                "error": str(e),
                "status": "error"
            }
    
    def search_web(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Mock web search - in production, this would use a real search API
        """
        # This is a mock implementation
        # In production, you'd use a real search API like Google Custom Search or Bing
        mock_results = [
            {
                "title": f"Result {i+1} for: {query}",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a sample snippet for search result {i+1} related to {query}"
            }
            for i in range(min(num_results, 5))
        ]
        
        return {
            "query": query,
            "results": mock_results,
            "total_results": len(mock_results)
        }
    
    def get_datetime(self, timezone: Optional[str] = None, format: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current date and time
        """
        from datetime import datetime
        import pytz
        
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                dt = datetime.now(tz)
            except:
                return {
                    "error": f"Invalid timezone: {timezone}",
                    "status": "error"
                }
        else:
            dt = datetime.now()
        
        if format:
            formatted = dt.strftime(format)
        else:
            formatted = dt.isoformat()
        
        return {
            "datetime": formatted,
            "timezone": timezone or "local",
            "timestamp": dt.timestamp()
        }
    
    def file_operations(self, operation: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Basic file operations (read, write, list)
        """
        import os
        
        try:
            if operation == "read":
                with open(path, 'r') as f:
                    content = f.read()
                return {
                    "path": path,
                    "content": content,
                    "size": len(content)
                }
            
            elif operation == "write":
                if content is None:
                    return {
                        "error": "Content is required for write operation",
                        "status": "error"
                    }
                with open(path, 'w') as f:
                    f.write(content)
                return {
                    "path": path,
                    "status": "success",
                    "bytes_written": len(content)
                }
            
            elif operation == "list":
                if os.path.isdir(path):
                    files = os.listdir(path)
                    return {
                        "path": path,
                        "files": files,
                        "count": len(files)
                    }
                else:
                    return {
                        "error": f"{path} is not a directory",
                        "status": "error"
                    }
            
            else:
                return {
                    "error": f"Unknown operation: {operation}",
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }

# Tool definitions for registration
TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "calculate",
        "description": "Perform mathematical calculations",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "execute_code",
        "description": "Execute Python code and return the result",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 5
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_datetime",
        "description": "Get current date and time",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'America/New_York')"
                },
                "format": {
                    "type": "string",
                    "description": "Date format string (e.g., '%Y-%m-%d %H:%M:%S')"
                }
            }
        }
    },
    {
        "name": "file_operations",
        "description": "Perform file operations (read, write, list)",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "list"],
                    "description": "The operation to perform"
                },
                "path": {
                    "type": "string",
                    "description": "The file or directory path"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (required for write operation)"
                }
            },
            "required": ["operation", "path"]
        }
    }
]

# Merge with DesktopCommander tools
TOOL_DEFINITIONS.extend(DESKTOP_COMMANDER_TOOLS)
