#!/usr/bin/env python3
"""
Demo script to test tool implementations locally without API calls
"""

from tool_implementations import ToolExecutor, TOOL_DEFINITIONS
import json

def main():
    print("=" * 80)
    print("🔧 Testing Tool Implementations Locally")
    print("=" * 80)
    
    # Initialize tool executor
    executor = ToolExecutor()
    
    # Test cases for each tool
    test_cases = [
        {
            "tool": "get_weather",
            "args": {"location": "San Francisco, CA", "unit": "celsius"},
            "description": "Get weather in San Francisco"
        },
        {
            "tool": "calculate",
            "args": {"expression": "15 * 0.15"},  # 15% of 100
            "description": "Calculate 15% (15 * 0.15)"
        },
        {
            "tool": "calculate",
            "args": {"expression": "625 ** 0.5"},  # Square root of 625
            "description": "Calculate square root of 625"
        },
        {
            "tool": "execute_code",
            "args": {
                "code": """
# Generate first 10 Fibonacci numbers
fib = [0, 1]
for i in range(8):
    fib.append(fib[-1] + fib[-2])
print("First 10 Fibonacci numbers:", fib)
"""
            },
            "description": "Generate Fibonacci numbers"
        },
        {
            "tool": "get_datetime",
            "args": {"timezone": "Asia/Tokyo", "format": "%Y-%m-%d %H:%M:%S"},
            "description": "Get current time in Tokyo"
        },
        {
            "tool": "search_web",
            "args": {"query": "machine learning basics", "num_results": 3},
            "description": "Search for machine learning information"
        },
        {
            "tool": "file_operations",
            "args": {"operation": "write", "path": "test_file.txt", "content": "Hello from tool test!"},
            "description": "Write to a test file"
        },
        {
            "tool": "file_operations",
            "args": {"operation": "read", "path": "test_file.txt"},
            "description": "Read the test file"
        },
        {
            "tool": "file_operations",
            "args": {"operation": "list", "path": "."},
            "description": "List files in current directory"
        }
    ]
    
    # Run each test
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Tool: {test['tool']}")
        print(f"   Args: {json.dumps(test['args'], indent=2)}")
        
        result = executor.execute(test['tool'], test['args'])
        
        if result['status'] == 'success':
            print(f"   ✅ Success:")
            print(f"   {json.dumps(result['result'], indent=2)}")
        else:
            print(f"   ❌ Error: {result['error']}")
        
        print("-" * 80)
    
    # Clean up test file
    try:
        import os
        os.remove("test_file.txt")
        print("\n🧹 Cleaned up test file")
    except:
        pass
    
    print("\n✨ Tool testing complete!")
    
    # Show available tools
    print("\n📋 Available Tools:")
    for tool in TOOL_DEFINITIONS:
        print(f"   - {tool['name']}: {tool['description']}")

if __name__ == "__main__":
    main()
