from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from tool_implementations import ToolExecutor

# Load environment variables
load_dotenv()

app = Flask(__name__)

@app.route('/invoke', methods=['POST'])
def invoke():
    # Get the request data
    data = request.json
    tool_name = data.get('tool_name')
    arguments = data.get('arguments', {})
    
    # Initialize tool executor
    executor = ToolExecutor()
    result = executor.execute(tool_name, arguments)
    
    # Return the result as JSON
    return jsonify(result)

if __name__ == '__main__':
    # Load the MCP configuration
    mcp_api_key = os.getenv('MCP_API_KEY', 'your-mcp-api-key')
    mcp_endpoint = os.getenv('MCP_ENDPOINT', 'https://mcp.example.com/api')
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000)

