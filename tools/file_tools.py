import os
import json
from app.registry import tool

MAX_FILE_READ_LENGTH = 3000

@tool(name="read_file", description="Читает файл из папки скрипта.",
      parameters={"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]})
def read_file(filename: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__)) # Учитываем вложенность
    root_dir = os.path.dirname(script_dir)
    file_path = os.path.join(root_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read(MAX_FILE_READ_LENGTH)
    except Exception as e:
        return f"Ошибка: {e}"

# Сюда же добавь функции save_note и list_notes (не забудь импорт os и json)
