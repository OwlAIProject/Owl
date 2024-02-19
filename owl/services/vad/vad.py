#
# vad.py
#
# Voice activity detection using Silero VAD. Includes a streaming version that allows audio to be
# passed in incrementally, in arbitrary chunk lengths, and yields speech segments as they are
# detected.
#
# Original: https://github.com/snakers4/silero-vad/blob/master/utils_vad.py
# and:      https://raw.githubusercontent.com/collabora/WhisperLive/main/whisper_live/vad.py
#

import logging
from math import floor
import os
from typing import Dict, List, Callable
import urllib.request

import torch
import numpy as np
import onnxruntime
from pydub import AudioSegment

from ...core.config import Configuration
from .time_segment import TimeSegment


logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    def __init__(self, config: Configuration, force_onnx_cpu=True):
        path = self._download(model_savedir=config.vad.vad_model_savedir)

        opts = onnxruntime.SessionOptions()
        opts.log_severity_level = 3

        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1

        if force_onnx_cpu and 'CPUExecutionProvider' in onnxruntime.get_available_providers():
            self.session = onnxruntime.InferenceSession(path, providers=['CPUExecutionProvider'], sess_options=opts)
        else:
            self.session = onnxruntime.InferenceSession(path, providers=['CUDAExecutionProvider'], sess_options=opts)

        self.reset_states()
        self.sample_rates = [8000, 16000]

    def _validate_input(self, x, sr: int):
        if x.dim() == 1:
            x = x.unsqueeze(0)
        if x.dim() > 2:
            raise ValueError(f"Too many dimensions for input audio chunk {x.dim()}")

        if sr != 16000 and (sr % 16000 == 0):
            step = sr // 16000
            x = x[:,::step]
            sr = 16000

        if sr not in self.sample_rates:
            raise ValueError(f"Supported sampling rates: {self.sample_rates} (or multiply of 16000)")

        if sr / x.shape[1] > 31.25:
            raise ValueError("Input audio chunk is too short")

        return x, sr

    def reset_states(self, batch_size=1):
        self._h = np.zeros((2, batch_size, 64)).astype('float32')
        self._c = np.zeros((2, batch_size, 64)).astype('float32')
        self._last_sr = 0
        self._last_batch_size = 0

    def __call__(self, x, sr: int):

        x, sr = self._validate_input(x, sr)
        batch_size = x.shape[0]

        if not self._last_batch_size:
            self.reset_states(batch_size)
        if (self._last_sr) and (self._last_sr != sr):
            self.reset_states(batch_size)
        if (self._last_batch_size) and (self._last_batch_size != batch_size):
            self.reset_states(batch_size)

        if sr in [8000, 16000]:
            ort_inputs = {'input': x.numpy(), 'h': self._h, 'c': self._c, 'sr': np.array(sr, dtype='int64')}
            ort_outs = self.session.run(None, ort_inputs)
            out, self._h, self._c = ort_outs
        else:
            raise ValueError()

        self._last_sr = sr
        self._last_batch_size = batch_size

        out = torch.tensor(out)
        return out

    def audio_forward(self, x, sr: int, num_samples: int = 512):
        outs = []
        x, sr = self._validate_input(x, sr)

        if x.shape[1] % num_samples:
            pad_num = num_samples - (x.shape[1] % num_samples)
            x = torch.nn.functional.pad(x, (0, pad_num), 'constant', value=0.0)

        self.reset_states(x.shape[0])
        for i in range(0, x.shape[1], num_samples):
            wavs_batch = x[:, i:i+num_samples]
            out_chunk = self.__call__(wavs_batch, sr)
            outs.append(out_chunk)

        stacked = torch.cat(outs, dim=1)
        return stacked.cpu()

    @staticmethod
    def _download(model_savedir: str, model_url="https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx"):
        os.makedirs(model_savedir, exist_ok=True)
        model_filepath = os.path.join(model_savedir, "silero_vad.onnx")
        if not os.path.exists(model_filepath):
            logger.info(f"Downloading VAD ONNX model to: {model_filepath}...")
            try:
                 urllib.request.urlretrieve(model_url, model_filepath)
            except Exception as e:
                raise RuntimeError("Failed to download VAD model")
        return model_filepath
    
    def get_speech_timestamps(
        self,
        audio: torch.Tensor,
        threshold: float = 0.5,
        sampling_rate: int = 16000,
        min_speech_duration_ms: int = 250,
        max_speech_duration_s: float = float('inf'),
        min_silence_duration_ms: int = 100,
        window_size_samples: int = 512,
        speech_pad_ms: int = 30,
        return_milliseconds: bool = False,
        progress_tracking_callback: Callable[[float], None] = None
    ) -> List[TimeSegment]:

        """
        This method is used for splitting long audios into speech chunks using silero VAD

        Parameters
        ----------
        audio: torch.Tensor, one dimensional
            One dimensional float torch.Tensor, other types are casted to torch if possible

        model: preloaded .jit silero VAD model

        threshold: float (default - 0.5)
            Speech threshold. Silero VAD outputs speech probabilities for each audio chunk, probabilities ABOVE this value are considered as SPEECH.
            It is better to tune this parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets.

        sampling_rate: int (default - 16000)
            Currently silero VAD models support 8000 and 16000 sample rates

        min_speech_duration_ms: int (default - 250 milliseconds)
            Final speech chunks shorter min_speech_duration_ms are thrown out

        max_speech_duration_s: int (default -  inf)
            Maximum duration of speech chunks in seconds
            Chunks longer than max_speech_duration_s will be split at the timestamp of the last silence that lasts more than 100ms (if any), to prevent agressive cutting.
            Otherwise, they will be split aggressively just before max_speech_duration_s.

        min_silence_duration_ms: int (default - 100 milliseconds)
            In the end of each speech chunk wait for min_silence_duration_ms before separating it

        window_size_samples: int (default - 1536 samples)
            Audio chunks of window_size_samples size are fed to the silero VAD model.
            WARNING! Silero VAD models were trained using 512, 1024, 1536 samples for 16000 sample rate and 256, 512, 768 samples for 8000 sample rate.
            Values other than these may affect model perfomance!!

        speech_pad_ms: int (default - 30 milliseconds)
            Final speech chunks are padded by speech_pad_ms each side

        return_milliseconds: bool (default - False)
            whether return timestamps in milliseconds (default - samples)

        visualize_probs: bool (default - False)
            whether draw prob hist or not

        progress_tracking_callback: Callable[[float], None] (default - None)
            callback function taking progress in percents as an argument

        Returns
        ----------
        speeches: List[TimeSegment]
            list containing ends and beginnings of speech chunks (samples or milliseconds based on
            return_milliseconds)
        """

        if not torch.is_tensor(audio):
            try:
                audio = torch.Tensor(audio)
            except:
                raise TypeError("Audio cannot be casted to tensor. Cast it manually")

        if len(audio.shape) > 1:
            for i in range(len(audio.shape)):  # trying to squeeze empty dimensions
                audio = audio.squeeze(0)
            if len(audio.shape) > 1:
                raise ValueError("More than one dimension in audio. Are you trying to process audio with 2 channels?")

        if sampling_rate > 16000 and (sampling_rate % 16000 == 0):
            step = sampling_rate // 16000
            sampling_rate = 16000
            audio = audio[::step]
            logger.warn("Sampling rate is a multiply of 16000, casting to 16000 manually!")
        elif sampling_rate != 16000 and sampling_rate != 8000:
            raise ValueError("sampling_rate must be either 16000 or 8000")
        else:
            step = 1

        if sampling_rate == 8000 and window_size_samples > 768:
            logger.warn('window_size_samples is too big for 8000 sampling_rate! Better set window_size_samples to 256, 512 or 768 for 8000 sample rate!')
        if window_size_samples not in [256, 512, 768, 1024, 1536]:
            logger.warn('Unusual window_size_samples! Supported window_size_samples:\n - [512, 1024, 1536] for 16000 sampling_rate\n - [256, 512, 768] for 8000 sampling_rate')

        self.reset_states()
        min_speech_samples = sampling_rate * min_speech_duration_ms / 1000
        speech_pad_samples = sampling_rate * speech_pad_ms / 1000
        max_speech_samples = sampling_rate * max_speech_duration_s - window_size_samples - 2 * speech_pad_samples
        min_silence_samples = sampling_rate * min_silence_duration_ms / 1000
        min_silence_samples_at_max_speech = sampling_rate * 98 / 1000

        audio_length_samples = len(audio)

        speech_probs = []
        for current_start_sample in range(0, audio_length_samples, window_size_samples):
            chunk = audio[current_start_sample : current_start_sample + window_size_samples]
            if len(chunk) < window_size_samples:
                chunk = torch.nn.functional.pad(chunk, (0, int(window_size_samples - len(chunk))))
            speech_prob = self(chunk, sampling_rate).item()
            speech_probs.append(speech_prob)
            # caculate progress and seng it to callback function
            progress = current_start_sample + window_size_samples
            if progress > audio_length_samples:
                progress = audio_length_samples
            progress_percent = (progress / audio_length_samples) * 100
            if progress_tracking_callback:
                progress_tracking_callback(progress_percent)

        triggered = False
        speeches = []
        current_speech = TimeSegment(start=-1, end=-1)
        neg_threshold = threshold - 0.15
        temp_end = 0 # to save potential segment end (and tolerate some silence)
        prev_end = next_start = 0 # to save potential segment limits in case of maximum segment size reached

        for i, speech_prob in enumerate(speech_probs):
            if (speech_prob >= threshold) and temp_end:
                temp_end = 0
                if next_start < prev_end:
                    next_start = window_size_samples * i

            if (speech_prob >= threshold) and not triggered:
                triggered = True
                current_speech.start = window_size_samples * i
                continue

            if triggered and (window_size_samples * i) - current_speech.start > max_speech_samples:
                if prev_end:
                    current_speech.end = prev_end
                    speeches.append(current_speech)
                    current_speech = TimeSegment(start=-1, end=-1)
                    if next_start < prev_end: # previously reached silence (< neg_thres) and is still not speech (< thres)
                        triggered = False
                    else:
                        current_speech.start = next_start
                    prev_end = next_start = temp_end = 0
                else:
                    current_speech.end = window_size_samples * i
                    speeches.append(current_speech)
                    current_speech = TimeSegment(start=-1, end=-1)
                    prev_end = next_start = temp_end = 0
                    triggered = False
                    continue

            if (speech_prob < neg_threshold) and triggered:
                if not temp_end:
                    temp_end = window_size_samples * i
                if ((window_size_samples * i) - temp_end) > min_silence_samples_at_max_speech : # condition to avoid cutting in very short silence
                    prev_end = temp_end
                if (window_size_samples * i) - temp_end < min_silence_samples:
                    continue
                else:
                    current_speech.end = temp_end
                    if (current_speech.end - current_speech.start) > min_speech_samples:
                        speeches.append(current_speech)
                    current_speech = TimeSegment(start=-1, end=-1)
                    prev_end = next_start = temp_end = 0
                    triggered = False
                    continue

        have_current_speech = current_speech.start >= 0
        if have_current_speech and (audio_length_samples - current_speech.start) > min_speech_samples:
            current_speech.end = audio_length_samples
            speeches.append(current_speech)

        for i, speech in enumerate(speeches):
            if i == 0:
                speech.start = int(max(0, speech.start - speech_pad_samples))
            if i != len(speeches) - 1:
                silence_duration = speeches[i+1].start - speech.end
                if silence_duration < 2 * speech_pad_samples:
                    speech.end += int(silence_duration // 2)
                    speeches[i+1].start = int(max(0, speeches[i+1].start - silence_duration // 2))
                else:
                    speech.end = int(min(audio_length_samples, speech.end + speech_pad_samples))
                    speeches[i+1].start = int(max(0, speeches[i+1].start - speech_pad_samples))
            else:
                speech.end = int(min(audio_length_samples, speech.end + speech_pad_samples))

        if return_milliseconds:
            samples_to_millis = (1000.0 / sampling_rate)
            for speech_dict in speeches:
                speech_dict.start = int(floor(speech_dict.start * samples_to_millis + 0.5))
                speech_dict.end = int(floor(speech_dict.end * samples_to_millis + 0.5))
        elif step > 1:
            for speech_dict in speeches:
                speech_dict.start *= step
                speech_dict.end *= step

        return speeches

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
        config : Configuration
            Program-wide configuration object, which is used to obtain the model directory.

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
            
    def is_inside_speech(self) -> bool:
        """
        Returns
        -------
        bool
            Whether the VAD is currently processing and inside of a speech segment that has not yet
            been terminated.
        """
        return not self._finished and self._triggered
    
    def is_speech_pending(self) -> bool:
        """
        Returns
        -------
        bool
            Whether a speech segment has not yet been returned and is pending (waiting for more
            audio samples to be finalized.) This can happen with speech segments that are too close
            to the end of a sample buffer.
        """
        return not self._finished and self._last_speech is not None

    def consume_samples(self, samples: torch.Tensor | AudioSegment, end_stream: bool = False, return_milliseconds: bool = False) -> List[TimeSegment]:
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
        List[TimeSegment]
            A list containing speech segments detected during this iteration. Timestamps are global
            (relative to the very beginning of the stream). Segments will be returned in order but
            may not be finalized until a subsequent call.
        """
        # Convert samples to tensor if needed
        if isinstance(samples, torch.Tensor):
            assert samples.dim() == 1
        elif isinstance(samples, AudioSegment):
            assert samples.frame_rate == 16000 and samples.sample_width == 2
            samples = torch.Tensor(samples.get_array_of_samples()) * (1.0 / 32767.0)
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
        first_speech_is_from_prev_call = False
        if self._last_speech:
            speeches.insert(0, self._last_speech)
            self._last_speech = None
            first_speech_is_from_prev_call = True
    
        return_last_speech = False
        for i, speech in enumerate(speeches):
            if i == 0 and not first_speech_is_from_prev_call:
                # This is the first speech segment for this call and it was *not* carried forward
                # from the previous one. Because of how we handle the last segment near the audio 
                # buffer boundary, we would have adjusted the start time of that sample already. In
                # this case, we can be assured that the sample will not overlap with any previous 
                # one.
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
                # This is the last speech segment in the array. We can only pad it out if we know
                # for sure that there will be no speech segment starting within < 
                # 2*speech_pad_samples of its endpoint. And to know that, we have to have enough
                # audio buffer remaining after it or be sure the stream has ended. If these
                # conditions are not true and we cannot look ahead far enough, we will *not* return
                # this sample and will instead process it on the next go around.
                samples_remaining_until_audio_end = audio_end - speech.end
                if end_stream or samples_remaining_until_audio_end >= (2 * speech_pad_samples):
                    return_last_speech = True
                    speech.end = int(min(audio_end, speech.end + speech_pad_samples))

        self._found_first_speech_in_stream |= len(speeches) > 0
        if len(speeches) > 0 and not return_last_speech:
            # We were unable to pad the last speech sample and have to save it until next time
            self._last_speech = speeches[-1]
            speeches = speeches[:-1]

        # Unit conversion
        if return_milliseconds:
            samples_to_millis = (1000.0 / self._sampling_rate)
            for speech_dict in speeches:
                speech_dict.start = int(floor(speech_dict.start * samples_to_millis + 0.5))
                speech_dict.end = int(floor(speech_dict.end * samples_to_millis + 0.5))
        
        return speeches