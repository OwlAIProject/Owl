#
# stream_vad.py
#
# Streaming voice activity detection using Silero VAD. A stateful object that allows audio to be
# passed in arbitrary chunk lengths, yielding speech segments as they are detected.
#

from math import floor
from typing import Dict, List

from pydub import AudioSegment
import torch

from ...core.config import Configuration
from .time_segment import TimeSegment
from .vad import VoiceActivityDetector


class StreamingVoiceActivityDetector(VoiceActivityDetector):
    def __init__(
        self,
        config: Configuration,
        threshold: float = 0.5,
        sampling_rate: int = 16000,
        min_speech_duration_ms: int = 250,
        max_speech_duration_s: float = float('inf'),
        min_silence_duration_ms: int = 100,
        window_size_samples: int = 512,
        speech_pad_ms: int = 30
    ):
        """
        Instantiates a Silero-based VAD that can perform voice activity detection in a streaming
        fashion, preserving state between calls and returning speech segments incrementally as they
        are detected.

        Parameters
        ----------
        threshold : float
            Speech threshold. Silero VAD outputs speech probabilities for each audio chunk, 
            probabilities ABOVE this value are considered as SPEECH. It is better to tune this
            parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets.

        sampling_rate : int
            Currently silero VAD models support 8000 and 16000 sample rates.

        min_speech_duration_ms : int
            Final speech chunks shorter min_speech_duration_ms are thrown out.

        max_speech_duration_s : int
            Maximum duration of speech chunks in seconds. Chunks longer than max_speech_duration_s 
            will be split at the timestamp of the last silence that lasts more than 100ms (if any),
            to prevent agressive cutting. Otherwise, they will be split aggressively just before
            max_speech_duration_s.

        min_silence_duration_ms : int
            In the end of each speech chunk wait for min_silence_duration_ms before separating it

        window_size_samples: int
            Audio chunks of window_size_samples size are fed to the silero VAD model.
            WARNING! Silero VAD models were trained using 512, 1024, 1536 samples for 16000 sample
            rate and 256, 512, 768 samples for 8000 sample rate. Values other than these may affect
            model perfomance!!

        speech_pad_ms : int
            Final speech chunks are padded by speech_pad_ms each side
        """
        assert sampling_rate == 16000

        super().__init__(config=config)
        self.reset_states()

        self._finished = False

        # VAD parameters
        self._threshold = threshold
        self._sampling_rate = sampling_rate
        self._min_speech_duration_ms = min_speech_duration_ms
        self._max_speech_duration_s = max_speech_duration_s
        self._min_silence_duration_ms = min_silence_duration_ms
        self._window_size_samples = window_size_samples
        self._speech_pad_ms = speech_pad_ms
        self._sample_buffer = None

        # Tracks the global offset from the start of the stream. At the start of consume_samples(),
        # this is the sample offset of the beginning of the samples that are being passed in
        # relative to the start of the first call to consume_samples().
        self._sample_offset = 0

        # State preserved across calls to consume_samples()
        self._triggered = False
        self._current_speech = TimeSegment(start=-1, end=-1)
        self._neg_threshold = threshold - 0.15
        self._temp_end = 0 # to save potential segment end (and tolerate some silence)
        self._prev_end = self._next_start = 0 # to save potential segment limits in case of maximum segment size reached

        # More tomfoolery required to carefully preserve state across repeated calls to
        # consume_samples()
        self._last_speech = None
        self._found_first_speech_in_stream = False
            
    def consume_samples(self, samples: torch.Tensor | AudioSegment, end_stream: bool = False, return_milliseconds: bool = False) -> List[Dict[str, int]]:
        """
        Injest samples from an audio stream and process them if there are enough. Any leftover
        samples that do not fill a complete window will be retained until a subsequent call unless
        the stream is terminated, in which case zero-padding will be used.

        Parameters
        ----------
        samples : torch.Tensor | pydub.AudioSegment
            One-dimensional tensor containing a single channel of audio samples. Also accepts a
            Pydub AudioSegment (must be in 16-bit 16KHz format).
        
        end_stream : bool
            Set this to true when the stream is finished and there will be no subsequent calls. A
            final set of samples or an empty tensor may be passed in.

        return_milliseconds : bool
            If true, all timestamps are in milliseconds from the very start of the stream.
            Otherwise, sample indices are used by default.

        Returns
        -------
        List[Dict[str, int]]
            A list of dictionaries containing speech segments detected during this iteration. Time-
            stamps are global (relative to the very beginning of the stream). Segments will be
            returned in-order but may not be finalized until a subsequent call.
        """
        # Convert samples to tensor if needed
        if isinstance(samples, torch.Tensor):
            assert samples.dim() == 1
        elif isinstance(samples, AudioSegment):
            assert samples.frame_rate == 16000 and samples.sample_width == 2
            samples = torch.Tensor(samples.get_array_of_samples()) * (1.0 / 65535.0)
        else:
            raise TypeError("'samples' must be either torch.Tensor or pydub.AudioSegment")

        # For now, we have not implemented state reset and this object cannot be reused
        if self._finished:
            raise RuntimeError("StreamingVoiceActivityDetector cannot be reused once streaming is finished")
        self._finished = end_stream

        # Append (or replace if already empty) samples
        if self._sample_buffer is not None:
            self._sample_buffer = torch.cat([ self._sample_buffer, samples ])
        else:
            self._sample_buffer = samples

        # We can proceed if we have an integral number of window-sized chunks *or* if we are ending
        # the stream (in which case, padding will be applied later)
        num_whole_windows = self._sample_buffer.numel() // self._window_size_samples
        if not end_stream and num_whole_windows == 0:
            return []
        
        # Precompute constants
        window_size_samples = self._window_size_samples
        sampling_rate = self._sampling_rate
        min_speech_samples = sampling_rate * self._min_speech_duration_ms / 1000
        speech_pad_samples = sampling_rate * self._speech_pad_ms / 1000
        max_speech_samples = sampling_rate * self._max_speech_duration_s - window_size_samples - 2 * speech_pad_samples
        min_silence_samples = sampling_rate * self._min_silence_duration_ms / 1000
        min_silence_samples_at_max_speech = sampling_rate * 98 / 1000
        threshold = self._threshold
        neg_threshold = self._neg_threshold

        # Run the whole windows through the VAD. If we are ending the stream, we can process the
        # final, partial window, too by zero padding it.
        audio_length_samples = len(self._sample_buffer)
        speech_probs = []
        current_start_sample = 0
        while current_start_sample < audio_length_samples:
            chunk = self._sample_buffer[current_start_sample : current_start_sample + window_size_samples]
            chunk_length = len(chunk)
            if chunk_length < window_size_samples:
                if end_stream:
                    chunk = torch.nn.functional.pad(chunk, (0, int(window_size_samples - chunk_length)))
                else:
                    # Do not process partial samples yet
                    break
            speech_prob = self(chunk, sampling_rate).item()
            speech_probs.append(speech_prob) 
            current_start_sample += chunk_length
        
        # Discard processed samples, taking care to leave unprocessed ones in the buffer
        if current_start_sample >= audio_length_samples:
            self._sample_buffer = None
        else:
            self._sample_buffer = self._sample_buffer[current_start_sample:]
    
        # Find speech segments in current batch of samples processed (as well as any segment that
        # may have started in a previous call to this function because we preserve state across
        # calls). Take care to do all math in terms of global sample offsets from now on.
        speeches = []
        for i, speech_prob in enumerate(speech_probs):
            segment_start = window_size_samples * i + self._sample_offset   # absolute sample index of start of segment relative to beginning of stream (not just what was passed in this call)
            
            if (speech_prob >= threshold) and self._temp_end:
                self._temp_end = 0
                if self._next_start < self._prev_end:
                    self._next_start = segment_start

            if (speech_prob >= threshold) and not self._triggered:
                self._triggered = True
                self._current_speech.start = segment_start
                continue

            if self._triggered and segment_start - self._current_speech.start > max_speech_samples:
                if self._prev_end:
                    self._current_speech.end = self._prev_end
                    speeches.append(self._current_speech)
                    self._current_speech = TimeSegment(start=-1, end=-1)
                    if self._next_start < self._prev_end:   # previously reached silence (< neg_thres) and is still not speech (< thres)
                        self._triggered = False
                    else:
                        self._current_speech.start = self._next_start
                    self._prev_end = self._next_start = self._temp_end = 0
                else:
                    self._current_speech.end = segment_start
                    speeches.append(self._current_speech)
                    self._current_speech = TimeSegment(start=-1, end=-1)
                    self._prev_end = self._next_start = self._temp_end = 0
                    self._triggered = False
                    continue

            if (speech_prob < neg_threshold) and self._triggered:
                if not self._temp_end:
                    self._temp_end = segment_start
                if (segment_start - self._temp_end) > min_silence_samples_at_max_speech:    # condition to avoid cutting in very short silence
                    self._prev_end = self._temp_end
                if segment_start - self._temp_end < min_silence_samples:
                    continue
                else:
                    self._current_speech.end = self._temp_end
                    if (self._current_speech.end - self._current_speech.start) > min_speech_samples:
                        speeches.append(self._current_speech)
                    self._current_speech = TimeSegment(start=-1, end=-1)
                    self._prev_end = self._next_start = self._temp_end = 0
                    self._triggered = False
                    continue

        # Update stream global sample offset to point to start of what will be processed next
        self._sample_offset += current_start_sample

        # When the stream has ended, don't forget to handle the very last in-progress segment!
        audio_end = self._sample_offset
        if end_stream:
            have_current_speech = self._current_speech.start >= 0
            if have_current_speech and (audio_end - self._current_speech.start) > min_speech_samples:
                self._current_speech.end = audio_end
                speeches.append(self._current_speech)
                self._current_speech = TimeSegment(start=-1, end=-1)
        
        # Add padding around speech segments. This is tricky do while streaming. We need to hang on
        # to the very last segment and re-insert it into the beginning of the list on the next call
        # to this function.
        if self._last_speech:
            speeches.insert(0, self._last_speech)
            self._last_speech = None
    
        for i, speech in enumerate(speeches):
            if not self._found_first_speech_in_stream and i == 0:
                speech.start = int(max(0, speech.start - speech_pad_samples))
            if i != len(speeches) - 1:
                silence_duration = speeches[i+1].start - speech.end
                if silence_duration < 2 * speech_pad_samples:
                    speech.end += int(silence_duration // 2)
                    speeches[i+1].start = int(max(0, speeches[i+1].start - silence_duration // 2))
                else:
                    speech.end = int(min(audio_end, speech.end + speech_pad_samples))
                    speeches[i+1].start = int(max(0, speeches[i+1].start - speech_pad_samples))
            else:
                # This is the last speech segment in the array. We always pluck the last element 
                # out and use it the next time this function is called. Therefore, the last segment
                # of all may encounter this code twice. Therefore, we must take care to only run
                # this *once*, at the *very end* of the stream.
                if end_stream:
                    speech.end = int(min(audio_end, speech.end + speech_pad_samples))

        self._found_first_speech_in_stream |= len(speeches) > 0
        if len(speeches) > 0 and not end_stream:
            # Save that last speech for now unless we are completely finished
            self._last_speech = speeches[-1]
            speeches = speeches[:-1]

        # Unit conversion
        if return_milliseconds:
            samples_to_millis = (1000.0 / self._sampling_rate)
            for speech_dict in speeches:
                speech_dict.start = int(floor(speech_dict.start * samples_to_millis + 0.5))
                speech_dict.end = int(floor(speech_dict.end * samples_to_millis + 0.5))
        
        return speeches