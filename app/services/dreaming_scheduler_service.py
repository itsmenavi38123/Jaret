from app.db import get_collection
from app.services.pattern_extraction_service import PatternExtractionService
from app.services.memory_consolidation_service import MemoryConsolidationService
from app.services.memory_learning_service import MemoryLearningService
from app.services.behavioral_pattern_recognition_service import BehavioralPatternRecognitionService
from app.services.dreaming_service import DreamingService
from app.services.org_playbook_generation_service import OrgPlaybookGenerationService


class DreamingSchedulerService:

    def __init__(self):
        self.users = get_collection("users")
        self.pattern_service = PatternExtractionService()
        self.consolidation_service = MemoryConsolidationService()
        self.learning_service = MemoryLearningService()
        self.behavior_service = BehavioralPatternRecognitionService()
        self.dreaming_service = DreamingService()
        self.org_playbook_service = OrgPlaybookGenerationService()

    async def run_daily_dreaming_pass(self):

        users = await self.users.find({}).to_list(length=None)

        for user in users:

            user_id = str(user["_id"])

            await self.pattern_service.extract_patterns(
                user_id=user_id
            )

            await self.consolidation_service.consolidate_patterns(
                user_id=user_id
            )

            await self.learning_service.extract_learnings(
                user_id=user_id
            )

            await self.behavior_service.extract_behavior_patterns(
                user_id=user_id
            )

            await self.dreaming_service.run_customer_dreaming(
                user_id=user_id
            )

        await self.org_playbook_service.generate_playbook_entries()