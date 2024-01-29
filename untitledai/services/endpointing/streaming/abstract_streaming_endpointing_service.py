from abc import ABC, abstractmethod

# Temporary to be replaced with VAD
class AbstractStreamingEndpointingService(ABC):
    
    @abstractmethod
    async def utterance_detected(self):
        pass

    