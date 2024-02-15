from abc import ABC, abstractmethod

class AbstractStreamingTranscriptionService(ABC):
    
    @abstractmethod
    async def send_audio(self, audio_chunk):
        pass
        
    @abstractmethod
    def set_callback(self, callback):
        pass
            
    @abstractmethod
    def set_stream_format(self, stream_format):
        pass
    