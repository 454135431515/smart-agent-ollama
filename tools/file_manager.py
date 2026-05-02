import os
import json
from app.registry import tool

MAX_FILE_READ_LENGTH = 3000
# Root directory of the project (where main.py is)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@tool(
    name="read_file",
    description="Reads a text file from the project root directory.",
    parameters={"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}
)
def read_file(filename: str) -> str:
    file_path = os.path.join(ROOT_DIR, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read(MAX_FILE_READ_LENGTH)
            if len(content) == MAX_FILE_READ_LENGTH:
                content += "\n[WARNING: File too large, truncated]"
        return f"File '{filename}' content:\n{content}"
    except FileNotFoundError:
        return f"Error: File '{filename}' not found."

@tool(
    name="save_note",
    description="Saves a note to the database.",
    parameters={"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}}, "required": ["title", "content"]}
)
def save_note(title: str, content: str) -> str:
    file_path = os.path.join(ROOT_DIR, "notes.json")
    notes =[]
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                notes = json.load(file)
        except json.JSONDecodeError:
            pass

    notes.append({"title": title, "content": content})
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(notes, file, ensure_ascii=False, indent=4)
    return f"Success! Note '{title}' saved."

@tool(
    name="list_notes",
    description="Lists all saved notes.",
    parameters={"type": "object", "properties": {}}
)
def list_notes() -> str:
    file_path = os.path.join(ROOT_DIR, "notes.json")
    if not os.path.exists(file_path):
        return "No notes found."
    with open(file_path, "r", encoding="utf-8") as file:
        notes = json.load(file)

    if not notes:
        return "Notes list is empty."
    return "Your notes:\n" + "\n".join([f"- {n['title']}" for n in notes])
