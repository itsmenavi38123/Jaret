from datetime import datetime


class MemoryPaths:

    @staticmethod
    def customer_root(
        user_id: str
    ) -> str:
        return f"/memories/customer_{user_id}"

    @staticmethod
    def customer_summary(
        user_id: str
    ) -> str:
        return f"/memories/customer_{user_id}/_summary.md"

    @staticmethod
    def customer_pinned(
        user_id: str
    ) -> str:
        return f"/memories/customer_{user_id}/_pinned"

    @staticmethod
    def customer_month_folder(
        user_id: str,
        dt: datetime
    ) -> str:
        return (
            f"/memories/customer_{user_id}/"
            f"{dt.year}/"
            f"{dt.month:02d}"
        )

    @staticmethod
    def customer_memory_file(
        user_id: str,
        agent_name: str,
        session_id: str,
        dt: datetime
    ) -> str:

        folder = MemoryPaths.customer_month_folder(
            user_id,
            dt
        )

        timestamp = dt.strftime(
            "%Y-%m-%dT%H-%M-%S"
        )

        return (
            f"{folder}/"
            f"{timestamp}-"
            f"{agent_name}-"
            f"{session_id}.json"
        )

    @staticmethod
    def org_playbook_root() -> str:
        return "/memories/org_playbook"