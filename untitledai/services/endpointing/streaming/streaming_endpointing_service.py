import asyncio
from .abstract_streaming_endpointing_service import AbstractStreamingEndpointingService

# Temporary to be replaced with VAD
class StreamingEndpointingService(AbstractStreamingEndpointingService):
    def __init__(self, timeout_interval: int, min_utterances: int, endpoint_callback=None):
        self.timeout_interval = timeout_interval
        self.min_utterances = min_utterances
        self._utterance_count = 0
        self._first_utterance_time = None
        self.endpoint_callback = endpoint_callback
        self._timeout_task = asyncio.create_task(self._check_timeout())
        self._endpoint_called = False

    async def utterance_detected(self):
        self._utterance_count += 1
        current_time = asyncio.get_event_loop().time()

        if self._first_utterance_time is None:
            self._first_utterance_time = current_time

    async def _check_timeout(self):
        while True:
            await asyncio.sleep(1)  
            if self._first_utterance_time is None:
                continue  #

            current_time = asyncio.get_event_loop().time()
            time_elapsed_since_first = current_time - self._first_utterance_time

            if (time_elapsed_since_first >= self.timeout_interval and
                self._utterance_count >= self.min_utterances and
                not self._endpoint_called):
                print("Conditions met, calling callback.")
                if self.endpoint_callback:
                    await self.endpoint_callback()
                    self._endpoint_called = True  
                    break 

        self._reset()

    def _reset(self):
        """
        Reset the utterance count, first utterance time, and endpoint_called flag.
        """
        self._utterance_count = 0
        self._first_utterance_time = None
        self._endpoint_called = False
        self._timeout_task = None

    def stop(self):
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None
