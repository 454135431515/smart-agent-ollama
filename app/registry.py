TOOL_REGISTRY = {}
TOOL_SCHEMAS =[]

def tool(name: str, description: str, parameters: dict):
    """Decorator to register a function as an LLM tool."""
    def decorator(func):
        TOOL_REGISTRY[name] = func
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
        return func
    return decorator
