from app.registry import tool

@tool(
    name="calculator",
    description="Mathematical calculator. Provide a valid math expression.",
    parameters={"type": "object", "properties": {"expression": {"type": "string", "description": "e.g. '2+2' or '100 * 92.5'"}}, "required": ["expression"]}
)
def calculator(expression: str) -> str:
    try:
        # Basic security against code injection
        allowed_chars = "0123456789+-*/()., "
        if not all(char in allowed_chars for char in expression):
            return "Error: Only numbers and basic math operators are allowed."

        expression = expression.replace(",", ".")
        result = eval(expression)
        return str(result)
    except Exception as error:
        return f"Calculation error: {error}"
