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

        print(
            "[Dreaming] ====================================="
        )
        print(
            "[Dreaming] Daily Dreaming Pass Started"
        )
        print(
            "[Dreaming] ====================================="
        )

        users = await self.users.find({}).to_list(
            length=None
        )

        print(
            f"[Dreaming] Found {len(users)} users"
        )

        for user in users:

            user_id = str(user["_id"])

            print(
                f"\n[Dreaming] Processing User: {user_id}"
            )

            try:

                pattern_count = await self.pattern_service.extract_patterns(
                    user_id=user_id
                )

                print(
                    f"[Dreaming] Pattern Extraction Complete | Created={pattern_count}"
                )

            except Exception as e:

                print(
                    f"[Dreaming] Pattern Extraction Failed | User={user_id} | Error={e}"
                )

            try:

                consolidated_count = await self.consolidation_service.consolidate_patterns(
                    user_id=user_id
                )

                print(
                    f"[Dreaming] Consolidation Complete | Consolidated={consolidated_count}"
                )

            except Exception as e:

                print(
                    f"[Dreaming] Consolidation Failed | User={user_id} | Error={e}"
                )

            try:

                learning_count = await self.learning_service.extract_learnings(
                    user_id=user_id
                )

                print(
                    f"[Dreaming] Learning Extraction Complete | Created={learning_count}"
                )

            except Exception as e:

                print(
                    f"[Dreaming] Learning Extraction Failed | User={user_id} | Error={e}"
                )

            try:

                behavior_count = await self.behavior_service.extract_behavior_patterns(
                    user_id=user_id
                )

                print(
                    f"[Dreaming] Behavior Extraction Complete | Created={behavior_count}"
                )

            except Exception as e:

                print(
                    f"[Dreaming] Behavior Extraction Failed | User={user_id} | Error={e}"
                )

            try:

                summary = await self.dreaming_service.run_customer_dreaming(
                    user_id=user_id
                )

                print(
                    f"[Dreaming] Summary Generation Complete | Length={len(summary) if summary else 0}"
                )

            except Exception as e:

                print(
                    f"[Dreaming] Summary Generation Failed | User={user_id} | Error={e}"
                )

        try:

            playbook_count = await self.org_playbook_service.generate_playbook_entries()

            print(
                f"[Dreaming] Org Playbook Generation Complete | Created={playbook_count}"
            )

        except Exception as e:

            print(
                f"[Dreaming] Org Playbook Generation Failed | Error={e}"
            )

        print(
            "[Dreaming] ====================================="
        )
        print(
            "[Dreaming] Daily Dreaming Pass Completed"
        )
        print(
            "[Dreaming] ====================================="
        )