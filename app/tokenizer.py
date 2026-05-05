import tiktoken

# Single shared encoder instance — imported by memory.py and agent.py
ENCODER = tiktoken.get_encoding("cl100k_base")
