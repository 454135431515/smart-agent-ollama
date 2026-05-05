import json
import os

from pydantic import BaseModel, Field

from app.registry import tool

MAX_FILE_READ_LENGTH = 3000
# Root directory of the project (where main.py is)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ReadFileArgs(BaseModel):
    filename: str = Field(description="Name of the file to read, relative to project root")


class SaveNoteArgs(BaseModel):
    title: str = Field(description="Title of the note")
    content: str = Field(description="Text content of the note")


class ListNotesArgs(BaseModel):
    pass


@tool(
    name="read_file",
    description="Reads a text file from the project root directory.",
    args_model=ReadFileArgs,
)
def read_file(filename: str) -> str:
    real_root = os.path.realpath(ROOT_DIR)
    file_path = os.path.realpath(os.path.join(ROOT_DIR, filename))
    if not file_path.startswith(real_root + os.sep) and file_path != real_root:
        return "Error: access denied: path outside project root."
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
    args_model=SaveNoteArgs,
)
def save_note(title: str, content: str) -> str:
    file_path = os.path.join(ROOT_DIR, "notes.json")
    notes = []
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
    args_model=ListNotesArgs,
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
