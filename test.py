# original: https://github.com/snakers4/silero-vad/blob/master/utils_vad.py
# and:      https://raw.githubusercontent.com/collabora/WhisperLive/main/whisper_live/vad.py
# example of a sliding window algorithm:
#           https://github.com/wiseman/py-webrtcvad/blob/master/example.py


import random

import torchaudio
import torch
from pydantic_yaml import parse_yaml_raw_as
from typing import List, Dict

from pydub import AudioSegment

from untitledai.services import VoiceActivityDetector, StreamingVoiceActivityDetector
from untitledai.core.config import Configuration

#TODO: instead of dicts, use dataclasses. These dict things are ridiculous. Shame on Silero.
#TODO: because streaming VAD may not yield a segment-in-progress for a long time, we cannot do endpointing
#      with timekeeping yet but we should add this ability. Should simply be a check of VAD state to see if
#      if it is currently inside of a segment.
class ConversationEndpointDetector:
    def __init__(self, config: Configuration, sampling_rate: int):
        assert sampling_rate == 16000
        self._finished = False
        self._streaming_vad = StreamingVoiceActivityDetector(config=config, sampling_rate=sampling_rate)
        self._current_conversation_start = None
        self._current_conversation_end = None
    
    def consume_samples(self, samples: torch.Tensor | AudioSegment, end_stream: bool = False) -> List[Dict[str, int]]:
        if self._finished:
            raise RuntimeError("ConversationEndpointDetector cannot be reused once streaming is finished")
        
        conversation_endpoint_duration = 5 * 60 * 1000  # 5 minutes
        conversations = []

        # Use VAD to detect voiced segments
        segments = self._streaming_vad.consume_samples(samples=samples, end_stream=end_stream, return_milliseconds=True)
        for segment in segments:
            if not self._current_conversation_end:
                # First segment we encounter is the start of a new conversation
                 self._current_conversation_start = segment["start"]
            else:
                # We are in a conversation now, detect the end point
                silence_duration = segment["start"] - self._current_conversation_end
                if silence_duration >= conversation_endpoint_duration:
                    conversations.append({ "start": self._current_conversation_start, "end": self._current_conversation_end })
                    self._current_conversation_start = segment["start"]
            self._current_conversation_end = segment["end"]
        
        # If stream is over, finish final conversation (if it exists)
        if end_stream and self._current_conversation_end:
            conversations.append({ "start": self._current_conversation_start, "end": self._current_conversation_end })
            self._current_conversation_start = None
            self._current_conversation_end = None
            self._finished = True

        return conversations    

if __name__ == "__main__":
    # Load config
    with open("config.yaml", "r") as fp:
        config = parse_yaml_raw_as(Configuration, fp.read())
    
    # Load audio into a tensor of samples
    filepath = "test.wav"
    format = "wav"
    audio = AudioSegment.from_file(filepath, format).set_channels(1).set_sample_width(2).set_frame_rate(16000)
    #samples = torch.Tensor(audio.get_array_of_samples()) * (1.0 / 65535.0)  # normalize, as expected by VAD
    samples = audio
    
    # # Run through VAD for reference result
    # vad = VoiceActivityDetector(config=config)
    # ts = vad.get_speech_timestamps(audio=samples, return_milliseconds=True)
    # ts_ref = ts
    # print("Reference:")
    # print(ts)
    # print("")

    #  # Find longest silence
    # max_silence_duration = 0
    # for i in range(1, len(ts)):
    #     silence_duration = ts[i]["start"] - ts[i-1]["end"]
    #     max_silence_duration = max(silence_duration, max_silence_duration)
    # print(f"Max silence = {max_silence_duration}")
    # exit()

    # Break up audio file into randomized number of segments to feed into VAD incrementally
    #typical_size = samples.numel() // 10
    typical_size = len(samples) // 10
    idx = 0
    chunks = []
    while idx < len(samples):
    #while idx < samples.numel():
        chunk_size = int(typical_size * (1.0 + random.uniform(0.1, 0.5)))
        chunks.append(samples[idx:idx+chunk_size])
        idx += chunk_size

    # Get speech timestamps using streaming VAD
    svad = StreamingVoiceActivityDetector(config=config, threshold=0.5)
    ts = []
    for i, chunk in enumerate(chunks):
        ts += svad.consume_samples(samples=chunk, return_milliseconds=True)
    ts += svad.consume_samples(samples=torch.Tensor([]), end_stream=True, return_milliseconds=True)
    print("Streaming:")
    print(ts)
    print("")

    # Collect into single file using Torch
    # audio_segments = []
    # for segment in ts:
    #     start = segment["start"]
    #     end = segment["end"]
    #     audio_segments.append(samples[start:end])
    # voice = torch.cat(audio_segments)
    # torchaudio.save("voiced.wav", voice.unsqueeze(0), 16000, bits_per_sample=16)

    # Collect into a single file using pydub
    i = 0
    audio_segments = []
    for segment in ts:
        start = segment["start"]
        end = segment["end"]
        audio_segments.append(audio[start:end])
    for i in range(1, len(audio_segments)):
        audio_segments[0] = audio_segments[0] + audio_segments[i]
    audio_segments[0].export("voiced.wav", "wav")

    # Split the file
    # i = 0
    # for segment in ts:
    #     start = segment["start"]
    #     end = segment["end"]
    #     filename = f"{i}.wav"
    #     audio[start:end].export(f"{i}.wav", "wav")
    #     print(f"Wrote {filename}")
    #     i += 1

    # # Compare VAD and streaming VAD
    # print("Comparison:")
    # print(f"  {len(ts_ref)} and {len(ts)}")
    # if len(ts_ref) == len(ts):
    #     for i in range(len(ts_ref)):
    #         if ts_ref[i]["start"] != ts[i]["start"] or ts_ref[i]["end"] != ts[i]["end"]:
    #             print(f"  {i} - {ts_ref[i]}, {ts[i]}")
    # print("")

    # Find longest silence
    max_silence_duration = 0
    for i in range(1, len(ts)):
        silence_duration = ts[i]["start"] - ts[i-1]["end"]
        max_silence_duration = max(silence_duration, max_silence_duration)
    print(f"Max silence = {max_silence_duration}")
        
    # # Conversation endpoints
    conversation_endpointer = ConversationEndpointDetector(config=config, sampling_rate=16000)
    conversations = []
    for chunk in chunks:
        conversations += conversation_endpointer.consume_samples(samples=chunk)
    conversations += conversation_endpointer.consume_samples(samples=torch.Tensor([]), end_stream=True)
    print("Conversations:")
    print(conversations)
    print("")

    # Write out files 
    i = 0
    for convo in conversations:
        start = convo["start"]
        end = convo["end"]
        filename = f"convo-{i}.wav"
        audio[start:end].export(filename, "wav")
        print(f"Wrote {filename}")
        i += 1
