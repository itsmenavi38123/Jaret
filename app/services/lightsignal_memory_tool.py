from datetime import datetime

from anthropic.tools import BetaAbstractMemoryTool
from anthropic.types.beta import (
    BetaMemoryTool20250818ViewCommand,
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818StrReplaceCommand,
    BetaMemoryTool20250818InsertCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818RenameCommand,
)

from app.services.sync_memory_service import sync_memory_service


class LightSignalMemoryTool(BetaAbstractMemoryTool):

    def __init__(
        self,
        user_id: str
    ):
        super().__init__()
        self.user_id = user_id

    def _validate_path(
        self,
        path: str
    ):

        customer_root = (
            f"/memories/customer_{self.user_id}/"
        )

        if path == "/memories":
            return

        if not path.startswith(
            customer_root
        ):
            raise ValueError(
                f"Memory access denied. "
                f"Path must start with "
                f"{customer_root}"
            )

    def view(
        self,
        command: BetaMemoryTool20250818ViewCommand
    ):

        if command.path == "/memories":
            command.path = (
                f"/memories/customer_{self.user_id}/"
            )

        self._validate_path(
            command.path
        )

        memory = sync_memory_service.get_by_path(
            command.path
        )

        if memory:
            result = {
                "type": "file",
                "path": command.path,
                "content": memory.get(
                    "content",
                    ""
                )
            }
        else:
            memories = sync_memory_service.get_by_path_prefix(
                command.path
            )

            result = {
                "type": "directory",
                "path": command.path,
                "items": [
                    memory.get("path")
                    for memory in memories[:100]
                ]
            }

        if (
            command.view_range
            and result.get("type") == "file"
        ):
            content = result.get(
                "content",
                ""
            )

            lines = content.splitlines()

            start = command.view_range[0]
            end = command.view_range[1]

            result["content"] = "\n".join(
                lines[start:end]
            )

        return str(result)

    def create(
        self,
        command: BetaMemoryTool20250818CreateCommand
    ):

        self._validate_path(
            command.path
        )

        existing = sync_memory_service.path_exists(
            command.path
        )

        if existing:
            raise ValueError(
                f"Memory already exists: {command.path}"
            )

        sync_memory_service.create_memory(
            {
                "user_id": self.user_id,
                "path": command.path,
                "content": command.file_text,
                "observation_type": "memory",
                "agent_name": "memory_tool",
                "confidence": "high",
                "outdated": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        return f"Created memory: {command.path}"

    def str_replace(
        self,
        command: BetaMemoryTool20250818StrReplaceCommand
    ):

        self._validate_path(
            command.path
        )

        memory = sync_memory_service.get_by_path(
            command.path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        content = memory.get(
            "content",
            ""
        )

        if command.old_str not in content:
            raise ValueError(
                "Target string not found"
            )

        updated_content = content.replace(
            command.old_str,
            command.new_str,
            1
        )

        sync_memory_service.update_memory(
            {
                "_id": memory["_id"]
            },
            {
                "$set": {
                    "content": updated_content,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return f"Updated memory: {command.path}"

    def insert(
        self,
        command: BetaMemoryTool20250818InsertCommand
    ):

        self._validate_path(
            command.path
        )

        memory = sync_memory_service.get_by_path(
            command.path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        content = memory.get(
            "content",
            ""
        )

        lines = content.splitlines()

        insert_line = max(
            0,
            min(
                command.insert_line,
                len(lines)
            )
        )

        lines.insert(
            insert_line,
            command.insert_text
        )

        updated_content = "\n".join(
            lines
        )

        sync_memory_service.update_memory(
            {
                "_id": memory["_id"]
            },
            {
                "$set": {
                    "content": updated_content,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return f"Inserted text into: {command.path}"

    def delete(
        self,
        command: BetaMemoryTool20250818DeleteCommand
    ):

        self._validate_path(
            command.path
        )

        memory = sync_memory_service.get_by_path(
            command.path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        sync_memory_service.delete_memory(
            {
                "_id": memory["_id"]
            }
        )

        return f"Deleted memory: {command.path}"

    def rename(
        self,
        command: BetaMemoryTool20250818RenameCommand
    ):

        self._validate_path(
            command.old_path
        )

        self._validate_path(
            command.new_path
        )

        memory = sync_memory_service.get_by_path(
            command.old_path
        )

        if not memory:
            raise ValueError(
                "Memory not found"
            )

        existing = sync_memory_service.path_exists(
            command.new_path
        )

        if existing:
            raise ValueError(
                f"Memory already exists: {command.new_path}"
            )

        sync_memory_service.update_memory(
            {
                "_id": memory["_id"]
            },
            {
                "$set": {
                    "path": command.new_path,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return (
            f"Renamed memory from "
            f"{command.old_path} "
            f"to "
            f"{command.new_path}"
        )

    def clear_all_memory(self):

        return (
            "clear_all_memory "
            "not supported for MongoDB backend"
        )