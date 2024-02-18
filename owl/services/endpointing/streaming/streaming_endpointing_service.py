import asyncio
from .abstract_streaming_endpointing_service import AbstractStreamingEndpointingService

class StreamingEndpointingService(AbstractStreamingEndpointingService):
    def __init__(self, timeout_seconds: int, min_utterances: int, endpoint_callback=None):
        self.timeout_seconds = timeout_seconds
        self.min_utterances = min_utterances
        self.endpoint_callback = endpoint_callback
        self._utterance_count = 0
        self._last_utterance_time = None
        self._endpoint_called = False
        self._timeout_task = asyncio.create_task(self._check_timeout())

    async def utterance_detected(self):
        current_time = asyncio.get_event_loop().time()
        self._last_utterance_time = current_time
        self._utterance_count += 1

    async def _check_timeout(self):
        while True:
            await asyncio.sleep(1)
            if self._last_utterance_time is None:
                continue

            current_time = asyncio.get_event_loop().time()
            time_elapsed_since_last = current_time - self._last_utterance_time

            if (time_elapsed_since_last >= self.timeout_seconds and
                self._utterance_count >= self.min_utterances and
                not self._endpoint_called):
                if self.endpoint_callback:
                    await self.endpoint_callback()
                self._reset()

    def _reset(self):
        self._utterance_count = 0
        self._last_utterance_time = None
        self._endpoint_called = False
        self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(self._check_timeout())

    def stop(self):
        if self._timeout_task:
            self._timeout_task.cancel()
