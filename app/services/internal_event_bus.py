from collections import defaultdict
from typing import Callable, Dict, List, Any
import asyncio


class InternalEventBus:

    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable):
        self.handlers[event_name].append(handler)

    async def publish(self, event_name: str, payload: Dict[str, Any]):

        handlers = self.handlers.get(event_name, [])

        for handler in handlers:

            try:

                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)

                else:
                    handler(payload)

            except Exception as e:
                print(f"Event bus handler error ({event_name}): {e}")


internal_event_bus = InternalEventBus()