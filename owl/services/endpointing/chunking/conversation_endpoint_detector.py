#
# conversation_endpoint_detector.py
#
# Conversation endpointing using simple timing threshold.
#

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List
import uuid

from pydub import AudioSegment
import torch

from ....core.config import Configuration
from ...vad.vad import StreamingVoiceActivityDetector


@dataclass
class ConversationEndpoints:
    start: datetime
    end: datetime

@dataclass
class DetectedConversation:
    """
    A unique conversation ID that should be assigned to conversation objects.
    """
    uuid: str

    """
    Conversation endpoint times (milliseconds) within capture.
    """
    endpoints: ConversationEndpoints

class ConversationEndpointDetector:
    def __init__(self, config: Configuration, start_time: datetime, sampling_rate: int):
        assert sampling_rate == 16000
        self._conversation_timeout_milliseconds = config.conversation_endpointing.timeout_seconds * 1000
        self._start_time = start_time
        self._finished = False
        self._sampling_rate = sampling_rate
        self._streaming_vad = StreamingVoiceActivityDetector(config=config, sampling_rate=sampling_rate)
        self._current_conversation_uuid = None
        self._current_conversation_start = None # milliseconds from start
        self._current_conversation_end = None   # milliseconds from start
        self._milliseconds_processed = 0

    def consume_samples(self, samples: torch.Tensor | AudioSegment | None, end_stream: bool = False) -> List[DetectedConversation]:
        if self._finished:
            raise RuntimeError("ConversationEndpointDetector cannot be reused once streaming is finished")

        if samples is None:
            samples = torch.Tensor([])

        duration_milliseconds = self._get_duration_milliseconds(samples=samples)

        conversations = []

        # Use VAD to detect voiced segments
        segments = self._streaming_vad.consume_samples(samples=samples, end_stream=end_stream, return_milliseconds=True)
        for segment in segments:
            if not self._current_conversation_end:
                # First segment we encounter is the start of a new conversation
                 self._current_conversation_uuid = uuid.uuid1().hex
                 self._current_conversation_start = segment.start
            else:
                # We are in a conversation now, detect the end point
                silence_duration = segment.start - self._current_conversation_end
                if silence_duration >= self._conversation_timeout_milliseconds:
                    # Produce finished conversation
                    conversations.append(self._make_conversation_object())

                    # Start new
                    self._current_conversation_uuid = uuid.uuid1().hex
                    self._current_conversation_start = segment.start
            self._current_conversation_end = segment.end    # if we have a start, ensure end is always set!

        self._milliseconds_processed += duration_milliseconds

        # If there were no segments, no speech segment is pending, and the VAD is not inside of a
        # new speech segment, then we may have just encountered a bunch of non-speech and must check
        # whether the current conversation has timed out.
        if self._current_conversation_end and len(segments) == 0 and \
           not self._streaming_vad.is_speech_pending() and \
           not self._streaming_vad.is_inside_speech():
            silence_duration = self._milliseconds_processed - self._current_conversation_end
            if silence_duration >= self._conversation_timeout_milliseconds:
                # Produce finished conversation
                conversations.append(self._make_conversation_object())

                # Wait for next conversation to start
                self._current_conversation_uuid = None
                self._current_conversation_start = None
                self._current_conversation_end = None

        # If stream is over, finish final conversation (if it exists)
        if end_stream and self._current_conversation_end:
            conversations.append(self._make_conversation_object())
            self._current_conversation_uuid = None
            self._current_conversation_start = None
            self._current_conversation_end = None
            self._finished = True

        return conversations

    def current_conversation_in_progress(self) -> DetectedConversation | None:
        if self._current_conversation_start is not None:
            return self._make_conversation_object()
        return None

    def _make_conversation_object(self):
        endpoints = ConversationEndpoints(
            start=self._start_time + timedelta(milliseconds=self._current_conversation_start),
            end=self._start_time + timedelta(milliseconds=self._current_conversation_end)
        )
        conversation = DetectedConversation(
            uuid=self._current_conversation_uuid,
            endpoints=endpoints
        )
        return conversation

    def _get_duration_milliseconds(self, samples: torch.Tensor | AudioSegment) -> int:
        if isinstance(samples, torch.Tensor):
            assert samples.dim() == 1
            return samples.numel() * 1000.0 / self._sampling_rate
        elif isinstance(samples, AudioSegment):
            assert samples.frame_rate == self._sampling_rate and samples.sample_width == 2
            return len(samples) # Pydub length reported in milliseconds
        else:
            raise TypeError("'samples' must be either torch.Tensor or pydub.AudioSegment")