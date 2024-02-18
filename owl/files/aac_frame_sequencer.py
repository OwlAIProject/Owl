#
# aac_frame_sequencer.py
#
# Looks for and extracts complete frames from an ADTS AAC stream.
#
# Useful resources:
#   - https://wiki.multimedia.cx/index.php/ADTS
#   - https://android.googlesource.com/platform/frameworks/av/+/jb-dev/media/libstagefright/codecs/aacdec/get_adts_header.cpp
#

from typing import Tuple


class AACFrameSequencer:
    def __init__(self):
        self._buffer = bytes()
    
    def get_next_frames(self, received_bytes: bytes) -> bytes:
        self._buffer += received_bytes
        output_frames = bytes()
        while True:
            found_header, advance_to_idx = self._find_next_header_candidate()
            self._buffer = self._buffer[advance_to_idx:]
            if not found_header:
                break
            frame_length = self._get_frame_length()
            if frame_length > len(self._buffer):
                break
            output_frames += self._buffer[0:frame_length]
            self._buffer = self._buffer[frame_length:]
        return output_frames
    
    def _find_next_header_candidate(self) -> Tuple[bool, int]:
        for i in range(len(self._buffer)):
            # Search for the 12 sync bits (FF Fx) followed by enough bytes to decode header
            if self._buffer[i] == 0xff:
                # Check if header is present in subsequent bytes, otherwise we have to stop at the
                # first 0xff for now
                bytes_remaining = len(self._buffer) - i
                if bytes_remaining < 7:
                    return (False, i)   # not sure yet but safe to discard preceding bytes
                if self._buffer[i + 1] & 0xf0 == 0xf0:
                    # Maybe! Need to verify some more information
                    layer = (self._buffer[i + 1] >> 1) & 3
                    mp4_sampling_frequency_index = (self._buffer[i + 2] >> 2) & 0xf
                    if layer == 0 and mp4_sampling_frequency_index == 8:
                        # Layer 0 and 16KHz sampling -> looks correct
                        return (True, i)    # found it
                    return (False, i + 2)   # invalid header, skip past these false sync bits
        
        # Not found, safe to discard everything
        return (False, len(self._buffer))
    
    def _get_frame_length(self):
        assert len(self._buffer) >= 7
        return ((self._buffer[3] & 0x03) << 11) | (self._buffer[4] << 3) | ((self._buffer[5] >> 5) & 0x07)