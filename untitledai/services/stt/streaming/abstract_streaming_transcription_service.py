from abc import ABC, abstractmethod

class AbstractStreamingTranscriptionService(ABC):
    
    @abstractmethod
    async def send_audio(self, audio_chunk):
        pass
        
    @abstractmethod
    async def on_utterance(self, callback):
        pass
    