from app.db import get_collection
from app.services.pattern_extraction_service import PatternExtractionService
from app.services.memory_consolidation_service import MemoryConsolidationService
from app.services.memory_learning_service import MemoryLearningService
from app.services.behavioral_pattern_recognition_service import BehavioralPatternRecognitionService
from app.services.dreaming_service import DreamingService
from app.services.org_playbook_generation_service import OrgPlaybookGenerationService
from app.services.peer_teaser_generation_service import PeerTeaserGenerationService
from datetime import datetime


class DreamingSchedulerService:

    def __init__(self):
        self.users = get_collection("users")
        self.pattern_service = PatternExtractionService()
        self.consolidation_service = MemoryConsolidationService()
        self.learning_service = MemoryLearningService()
        self.behavior_service = BehavioralPatternRecognitionService()
        self.dreaming_service = DreamingService()
        self.org_playbook_service = OrgPlaybookGenerationService()
        self.teaser_generation_service = PeerTeaserGenerationService()

    async def run_daily_dreaming_pass(self):
        playbook_count = 0
        teaser_count = 0

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

        try:
            pass_date = datetime.now().strftime("%Y-%m-%d")
            teaser_count = await self.teaser_generation_service.generate_teasers_from_playbook(
                proposed_by_name=f"dreaming pass {pass_date}"
            )
            print(
                f"[Dreaming] Peer Teaser Generation Complete | Created={teaser_count}"
            )
        except Exception as e:
            print(
                f"[Dreaming] Peer Teaser Generation Failed | Error={e}"
            )

        # Log this daily dreaming pass in the dreaming_runs audit collection
        try:
            memories_col = get_collection("customer_memory")
            memories = await memories_col.find({
                "observation_type": {"$in": ["pattern", "learning", "behavior_pattern"]},
                "outdated": False
            }).to_list(length=1000)
            contributors = set(m.get("user_id") for m in memories if m.get("user_id"))
            contributors_count = len(contributors)
            
            runs_col = get_collection("dreaming_runs")
            last_run = await runs_col.find_one(sort=[("pass_number", -1)])
            next_pass_num = (last_run.get("pass_number", 0) + 1) if last_run else 39
            
            summary_str = f"{playbook_count} insight{'s' if playbook_count != 1 else ''} generated → org playbook" if playbook_count > 0 else "no insight cleared the bar · nothing written"
            full_log_str = (
                f"Daily dreaming pass completed successfully.\n"
                f"- Processed {len(memories)} active customer memories.\n"
                f"- Total unique business contributors: {contributors_count}.\n"
                f"- Generated {playbook_count} new cross-customer playbook insights.\n"
                f"- Proposed {teaser_count} new onboarding peer teasers."
            )
            
            import uuid
            await runs_col.insert_one({
                "_id": str(uuid.uuid4()),
                "pass_number": next_pass_num,
                "segment_name": "all active segments",
                "timestamp": datetime.utcnow(),
                "contributors_count": contributors_count,
                "insights_generated_count": playbook_count,
                "summary_text": summary_str,
                "full_log": full_log_str,
                "status": "success"
            })
            print(f"[Dreaming] Successfully logged dreaming pass #{next_pass_num}")
        except Exception as log_err:
            print(f"[Dreaming] Failed to log dreaming pass: {log_err}")

        print(
            "[Dreaming] ====================================="
        )
        print(
            "[Dreaming] Daily Dreaming Pass Completed"
        )
        print(
            "[Dreaming] ====================================="
        )

    async def run_customer_dreaming_pipeline(self, user_id: str):
        """Runs the complete memory dreaming extraction pipeline for a single customer on-demand."""
        print(f"[Dreaming] Running on-demand customer dreaming pipeline for: {user_id}")
        
        # 1. Pattern extraction
        try:
            pattern_count = await self.pattern_service.extract_patterns(user_id=user_id)
            print(f"[Dreaming] On-Demand Pattern Extraction Complete | Created={pattern_count}")
        except Exception as e:
            print(f"[Dreaming] On-Demand Pattern Extraction Failed | User={user_id} | Error={e}")
            
        # 2. Consolidation
        try:
            consolidated_count = await self.consolidation_service.consolidate_patterns(user_id=user_id)
            print(f"[Dreaming] On-Demand Consolidation Complete | Consolidated={consolidated_count}")
        except Exception as e:
            print(f"[Dreaming] On-Demand Consolidation Failed | User={user_id} | Error={e}")
            
        # 3. Learning extraction
        try:
            learning_count = await self.learning_service.extract_learnings(user_id=user_id)
            print(f"[Dreaming] On-Demand Learning Extraction Complete | Created={learning_count}")
        except Exception as e:
            print(f"[Dreaming] On-Demand Learning Extraction Failed | User={user_id} | Error={e}")
            
        # 4. Behavior extraction
        try:
            behavior_count = await self.behavior_service.extract_behavior_patterns(user_id=user_id)
            print(f"[Dreaming] On-Demand Behavior Extraction Complete | Created={behavior_count}")
        except Exception as e:
            print(f"[Dreaming] On-Demand Behavior Extraction Failed | User={user_id} | Error={e}")
            
        # 5. Summary generation
        try:
            summary = await self.dreaming_service.run_customer_dreaming(user_id=user_id)
            print(f"[Dreaming] On-Demand Summary Generation Complete | Length={len(summary) if summary else 0}")
        except Exception as e:
            print(f"[Dreaming] On-Demand Summary Generation Failed | User={user_id} | Error={e}")