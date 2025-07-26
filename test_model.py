import os
import json
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv
from fine_tune import QwenFineTuner, Tool
from tool_implementations import ToolExecutor, TOOL_DEFINITIONS

# Load environment variables
load_dotenv()

class QwenModelWithTools:
    """
    Wrapper class for using the fine-tuned Qwen model with tool support
    """
    
    def __init__(self, api_key: str = None):
        self.fine_tuner = QwenFineTuner(api_key)
        self.tool_executor = ToolExecutor()
        
        # Register all tools
        for tool_def in TOOL_DEFINITIONS:
            tool = Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"]
            )
            self.fine_tuner.add_tool(tool)
    
    def process_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process tool calls and return results"""
        results = []
        
        for call in tool_calls:
            function_name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"])
            
            print(f"\n🔧 Executing tool: {function_name}")
            print(f"   Arguments: {arguments}")
            
            result = self.tool_executor.execute(function_name, arguments)
            results.append({
                "tool_call_id": call["id"],
                "result": result
            })
            
            print(f"   Result: {result}")
        
        return results
    
    def chat(self, message: str) -> str:
        """Chat with the model and handle tool calls if needed"""
        print(f"\n👤 User: {message}")
        
        try:
            # Get model response
            response = self.fine_tuner.test_model_with_tools(message)
            
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                
                # Check if the model wants to use tools
                if "tool_calls" in choice.get("message", {}):
                    tool_calls = choice["message"]["tool_calls"]
                    
                    # Execute the tools
                    tool_results = self.process_tool_calls(tool_calls)
                    
                    # Format final response
                    final_response = "Based on the tool execution:\n"
                    for result in tool_results:
                        if result["result"]["status"] == "success":
                            final_response += f"- {json.dumps(result['result']['result'], indent=2)}\n"
                        else:
                            final_response += f"- Error: {result['result']['error']}\n"
                    
                    return final_response
                else:
                    # Direct response without tools
                    return choice["message"]["content"]
            else:
                return "Error: No response from model"
                
        except Exception as e:
            return f"Error: {str(e)}"

def run_examples():
    """Run example queries to demonstrate the model's capabilities"""
    
    # Initialize the model
    model = QwenModelWithTools()
    
    # Example queries
    examples = [
        "What's the weather in San Francisco?",
        "Calculate the square root of 625",
        "What's 15% of 240?",
        "Write Python code to generate the first 10 Fibonacci numbers",
        "What time is it in Tokyo?",
        "Search for information about machine learning",
        "Explain quantum computing in simple terms",  # This won't use tools
    ]
    
    print("=" * 80)
    print("🤖 Qwen3 Fine-Tuned Model with Tool Support - Demo")
    print("=" * 80)
    
    for example in examples:
        response = model.chat(example)
        print(f"\n🤖 Assistant: {response}")
        print("-" * 80)

def interactive_mode():
    """Run the model in interactive mode"""
    model = QwenModelWithTools()
    
    print("=" * 80)
    print("🤖 Qwen3 Fine-Tuned Model - Interactive Mode")
    print("   Type 'quit' to exit")
    print("=" * 80)
    
    while True:
        try:
            user_input = input("\n👤 You: ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            response = model.chat(user_input)
            print(f"\n🤖 Assistant: {response}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

def main():
    """Main function"""
    import sys
    
    # Check if API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  Warning: OPENROUTER_API_KEY environment variable not set!")
        print("   Please set it in your .env file or export it:")
        print("   export OPENROUTER_API_KEY='your-api-key-here'")
        print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        run_examples()

if __name__ == "__main__":
    main()
