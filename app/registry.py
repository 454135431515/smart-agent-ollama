from pydantic import BaseModel, ValidationError

TOOL_REGISTRY = {}
TOOL_SCHEMAS = []


def _clean_schema(schema: dict) -> dict:
    """Strip Pydantic-specific noise, keep what OpenAI tool-calling expects."""
    schema.pop("title", None)
    schema.pop("$defs", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return schema


def tool(name: str, description: str, args_model: type[BaseModel]):
    """Decorator that registers a function as an LLM tool with Pydantic validation."""
    def decorator(func):
        def wrapper(**kwargs):
            validated = args_model(**kwargs)
            return func(**validated.model_dump())

        TOOL_REGISTRY[name] = wrapper

        raw_schema = args_model.model_json_schema()
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": _clean_schema(raw_schema),
            }
        })
        return func
    return decorator
