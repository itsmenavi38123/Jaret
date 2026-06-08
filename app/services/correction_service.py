from datetime import datetime

from app.services.customer_memory_service import CustomerMemoryService
from app.utils.memory_factory import MemoryFactory


class CorrectionService:

    def __init__(self):
        self.memory_service = CustomerMemoryService()

    async def apply_user_correction(
        self,
        original_memory_id: str,
        corrected_content: str
    ) -> str:

        return await self._create_correction(
            original_memory_id=original_memory_id,
            corrected_content=corrected_content,
            authority="user"
        )

    async def apply_agent_correction(
        self,
        original_memory_id: str,
        corrected_content: str
    ) -> str:

        return await self._create_correction(
            original_memory_id=original_memory_id,
            corrected_content=corrected_content,
            authority="agent_self"
        )

    async def apply_dreaming_correction(
        self,
        original_memory_id: str,
        corrected_content: str
    ) -> str:

        return await self._create_correction(
            original_memory_id=original_memory_id,
            corrected_content=corrected_content,
            authority="dreaming_pass"
        )

    async def handle_contradiction(
        self,
        memory_id_1: str,
        memory_id_2: str,
        correction_content: str
    ) -> str:

        memory_1 = await self.memory_service.get_memory_by_id(
            memory_id_1
        )

        memory_2 = await self.memory_service.get_memory_by_id(
            memory_id_2
        )

        if not memory_1 or not memory_2:
            raise ValueError(
                "Contradicting memories not found"
            )

        await self.memory_service.set_under_review(
            memory_id_1,
            True
        )

        await self.memory_service.set_under_review(
            memory_id_2,
            True
        )

        correction_memory = MemoryFactory.create_memory(
            user_id=memory_1["user_id"],
            observation_type="correction",
            content=correction_content,
            authority="dreaming_pass",
            confidence="medium",
            tags=["correction", "contradiction"]
        )

        return await self.memory_service.create_memory(
            correction_memory
        )

    async def mark_memory_under_review(
        self,
        memory_id: str
    ):

        await self.memory_service.set_under_review(
            memory_id=memory_id,
            under_review=True
        )

    async def _create_correction(
        self,
        original_memory_id: str,
        corrected_content: str,
        authority: str
    ) -> str:

        original_memory = await self.memory_service.get_memory_by_id(
            original_memory_id
        )

        if not original_memory:
            raise ValueError(
                "Original memory not found"
            )

        correction_path = (
            f"{original_memory['path']}_correction_"
            f"{int(datetime.utcnow().timestamp())}"
        )

        correction_memory = MemoryFactory.create_memory(
            user_id=original_memory["user_id"],
            observation_type="correction",
            content=corrected_content,
            authority=authority,
            confidence="high",
            tags=["correction"],
            path=correction_path
        )

        correction_id = await self.memory_service.create_memory(
            correction_memory
        )

        await self.memory_service.mark_outdated(
            original_memory_id
        )

        await self.memory_service.set_superseded_by(
            memory_id=original_memory_id,
            superseded_by=correction_id
        )

        return correction_id