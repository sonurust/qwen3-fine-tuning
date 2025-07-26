import os
import json
from typing import List, Dict, Any, Optional
import requests
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "qwen/qwen-2.5-72b-instruct"  # OpenRouter model identifier

@dataclass
class Tool:
    """Represents a tool/function that the model can use"""
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class QwenFineTuner:
    """Fine-tuning manager for Qwen3 model via OpenRouter"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/qwen-finetuning",
            "X-Title": "Qwen Fine-Tuning with Tools"
        }
        
        self.tools: List[Tool] = []
        self.training_data: List[Dict[str, Any]] = []
    
    def add_tool(self, tool: Tool):
        """Add a tool to the model's capability"""
        self.tools.append(tool)
        print(f"Added tool: {tool.name}")
    
    def create_training_example(self, 
                              user_message: str, 
                              assistant_message: str,
                              tool_calls: Optional[List[Dict[str, Any]]] = None,
                              tool_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a training example with optional tool usage"""
        messages = [
            {"role": "user", "content": user_message}
        ]
        
        if tool_calls and tool_results:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_message,
                "tool_calls": tool_calls
            })
            
            # Add tool results
            for i, result in enumerate(tool_results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_calls[i]["id"],
                    "content": json.dumps(result)
                })
            
            # Add final assistant response
            messages.append({
                "role": "assistant",
                "content": assistant_message
            })
        else:
            # Simple response without tools
            messages.append({
                "role": "assistant",
                "content": assistant_message
            })
        
        return {
            "messages": messages,
            "tools": [tool.to_openai_format() for tool in self.tools] if self.tools else None
        }
    
    def add_training_example(self, example: Dict[str, Any]):
        """Add a training example to the dataset"""
        self.training_data.append(example)
        print(f"Added training example {len(self.training_data)}")
    
    def save_training_data(self, filename: str = "training_data.jsonl"):
        """Save training data in JSONL format"""
        with open(filename, 'w') as f:
            for example in self.training_data:
                f.write(json.dumps(example) + '\n')
        print(f"Saved {len(self.training_data)} training examples to {filename}")
    
    def test_model_with_tools(self, prompt: str) -> Dict[str, Any]:
        """Test the model with tool support"""
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "tools": [tool.to_openai_format() for tool in self.tools] if self.tools else None,
            "tool_choice": "auto" if self.tools else None
        }
        
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    def create_custom_prompt_template(self, system_prompt: str) -> str:
        """Create a custom prompt template for fine-tuning"""
        return f"""<|system|>
{system_prompt}

Available tools:
{json.dumps([tool.to_openai_format() for tool in self.tools], indent=2)}
<|end|>

<|user|>
{{user_input}}
<|end|>

<|assistant|>
"""

# Example tools
def create_example_tools():
    """Create example tools for demonstration"""
    
    # Weather tool
    weather_tool = Tool(
        name="get_weather",
        description="Get the current weather in a given location",
        parameters={
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
    )
    
    # Calculator tool
    calculator_tool = Tool(
        name="calculate",
        description="Perform mathematical calculations",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    )
    
    # Code execution tool
    code_tool = Tool(
        name="execute_code",
        description="Execute Python code and return the result",
        parameters={
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
    )
    
    return [weather_tool, calculator_tool, code_tool]

def main():
    """Main function to demonstrate fine-tuning setup"""
    
    # Initialize fine-tuner
    fine_tuner = QwenFineTuner()
    
    # Add example tools
    tools = create_example_tools()
    for tool in tools:
        fine_tuner.add_tool(tool)
    
    # Create training examples
    # Example 1: Weather query with tool usage
    example1 = fine_tuner.create_training_example(
        user_message="What's the weather like in New York?",
        assistant_message="I'll check the weather in New York for you.",
        tool_calls=[{
            "id": "call_001",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": "New York, NY"})
            }
        }],
        tool_results=[{
            "temperature": 72,
            "condition": "Partly cloudy",
            "humidity": 65
        }]
    )
    fine_tuner.add_training_example(example1)
    
    # Example 2: Calculation with tool usage
    example2 = fine_tuner.create_training_example(
        user_message="Calculate the square root of 144",
        assistant_message="I'll calculate that for you.",
        tool_calls=[{
            "id": "call_002",
            "type": "function",
            "function": {
                "name": "calculate",
                "arguments": json.dumps({"expression": "144 ** 0.5"})
            }
        }],
        tool_results=[{
            "result": 12.0
        }]
    )
    fine_tuner.add_training_example(example2)
    
    # Example 3: Simple response without tools
    example3 = fine_tuner.create_training_example(
        user_message="What is machine learning?",
        assistant_message="Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing algorithms that can analyze data, identify patterns, and make decisions with minimal human intervention."
    )
    fine_tuner.add_training_example(example3)
    
    # Save training data
    fine_tuner.save_training_data()
    
    # Create custom system prompt
    system_prompt = """You are a helpful AI assistant with access to various tools. 
When a user asks a question that requires using a tool, you should:
1. Identify the appropriate tool
2. Extract the necessary parameters
3. Call the tool with proper arguments
4. Provide a helpful response based on the tool's output

Always be concise and accurate in your responses."""
    
    custom_template = fine_tuner.create_custom_prompt_template(system_prompt)
    
    # Save the custom template
    with open("prompt_template.txt", "w") as f:
        f.write(custom_template)
    
    print("\nFine-tuning setup complete!")
    print(f"- Training data saved to: training_data.jsonl")
    print(f"- Prompt template saved to: prompt_template.txt")
    print(f"- Number of tools configured: {len(fine_tuner.tools)}")
    print(f"- Number of training examples: {len(fine_tuner.training_data)}")

if __name__ == "__main__":
    main()
