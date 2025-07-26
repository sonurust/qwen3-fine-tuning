# Qwen3 Fine-Tuning with Tool Support via OpenRouter

This project provides a complete setup for fine-tuning the Qwen3-235B-A22B-Thinking-2507 model via OpenRouter with custom tool support.

## Features

- 🔧 **Tool Support**: Integrated support for function calling/tools
- 🎯 **Fine-Tuning Ready**: Complete setup for customizing the model
- 🚀 **OpenRouter Integration**: Uses OpenRouter API for model access
- 📊 **Training Data Management**: JSONL format for training examples
- 🛡️ **Safe Code Execution**: Sandboxed Python code execution
- 🌐 **Multiple Tools**: Weather, calculator, code execution, web search, datetime, and file operations

## Project Structure

```
qween3-latest/
├── .env                    # Environment variables (add your API key here)
├── config.json            # Fine-tuning configuration
├── fine_tune.py           # Main fine-tuning script
├── tool_implementations.py # Tool function implementations
├── test_model.py          # Testing and demo script
├── requirements.txt       # Python dependencies
├── training_data.jsonl    # Training examples (generated)
├── prompt_template.txt    # Custom prompt template (generated)
└── README.md             # This file
```

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set OpenRouter API Key**
   
   Add your OpenRouter API key to the `.env` file:
   ```bash
   echo "OPENROUTER_API_KEY=your-api-key-here" >> .env
   ```
   
   Or export it in your shell:
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```

3. **Generate Training Data**
   ```bash
   python fine_tune.py
   ```
   
   This will create:
   - `training_data.jsonl`: Training examples with tool usage
   - `prompt_template.txt`: Custom prompt template

## Usage

### Test the Model

Run example queries:
```bash
python test_model.py
```

Run in interactive mode:
```bash
python test_model.py --interactive
```

### Available Tools

1. **get_weather**: Get weather information for a location
2. **calculate**: Perform mathematical calculations
3. **execute_code**: Run Python code safely
4. **search_web**: Search for information (mock implementation)
5. **get_datetime**: Get current date/time in any timezone
6. **file_operations**: Read, write, or list files

### Adding Custom Tools

1. Define your tool in `tool_implementations.py`:
   ```python
   def my_custom_tool(self, param1: str, param2: int) -> Dict[str, Any]:
       # Your implementation
       return {"result": "..."}
   ```

2. Add tool definition to `TOOL_DEFINITIONS`:
   ```python
   {
       "name": "my_custom_tool",
       "description": "Description of what the tool does",
       "parameters": {
           "type": "object",
           "properties": {
               "param1": {"type": "string", "description": "..."},
               "param2": {"type": "integer", "description": "..."}
           },
           "required": ["param1"]
       }
   }
   ```

3. Register in the `ToolExecutor.__init__`:
   ```python
   self.tools["my_custom_tool"] = self.my_custom_tool
   ```

### Creating Training Examples

```python
from fine_tune import QwenFineTuner, Tool

# Initialize fine-tuner
fine_tuner = QwenFineTuner()

# Add your tools
tool = Tool(
    name="my_tool",
    description="Tool description",
    parameters={...}
)
fine_tuner.add_tool(tool)

# Create training example with tool usage
example = fine_tuner.create_training_example(
    user_message="User query",
    assistant_message="Assistant response",
    tool_calls=[{
        "id": "call_001",
        "type": "function",
        "function": {
            "name": "my_tool",
            "arguments": json.dumps({"param": "value"})
        }
    }],
    tool_results=[{"result": "tool output"}]
)

# Add to training data
fine_tuner.add_training_example(example)

# Save
fine_tuner.save_training_data()
```

## Configuration

Edit `config.json` to customize:
- Model parameters
- Fine-tuning hyperparameters
- Tool settings
- Training configuration
- Output directories

## API Rate Limits

The configuration includes rate limiting settings:
- 60 requests per minute
- 90,000 tokens per minute

Adjust these in `config.json` based on your OpenRouter plan.

## Production Considerations

1. **Real APIs**: Replace mock implementations in `tool_implementations.py` with real API calls
2. **Security**: Review and enhance the code execution sandbox
3. **Error Handling**: Add comprehensive error handling and logging
4. **Monitoring**: Implement usage tracking and monitoring
5. **Caching**: Add caching for frequently used tool results

## Troubleshooting

- **API Key Issues**: Ensure your OpenRouter API key is correctly set
- **Rate Limits**: Check if you're hitting rate limits and adjust accordingly
- **Tool Errors**: Check tool implementation logs for detailed error messages

## License

This project is provided as-is for educational and development purposes.
