import asyncio
import logging
from datetime import datetime

from app.db import get_collection


logger = logging.getLogger(__name__)


class MemoryFailureService:

    def __init__(self):
        self.failures = get_collection(
            "memory_failures"
        )

    async def execute(
        self,
        operation_name: str,
        customer_id: str,
        callback,
        agent_name: str | None = None
    ):

        try:
            return await callback()

        except Exception:

            await asyncio.sleep(1)

            try:
                return await callback()

            except Exception as exc:

                await asyncio.sleep(3)

                try:
                    return await callback()

                except Exception as final_exc:

                    logger.exception(
                        "Memory operation failed"
                    )

                    await self.create_failure_popup(
                        operation_name=operation_name,
                        customer_id=customer_id,
                        agent_name=agent_name,
                        error=str(final_exc)
                    )

                    return None

    async def create_failure_popup(
        self,
        operation_name: str,
        customer_id: str,
        error: str,
        agent_name: str | None = None
    ):

        document = {
            "timestamp": datetime.utcnow(),
            "operation": operation_name,
            "customer_id": customer_id,
            "agent_name": agent_name,
            "error": error,
            "resolved": False
        }

        await self.failures.insert_one(
            document
        )