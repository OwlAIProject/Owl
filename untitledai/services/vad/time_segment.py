#
# time_segment.py
#
# Data structure for defining a segment of time where the units can be represented as integers
# (samples, milliseconds). Used by VAD and conversation endpointing to represent voiced segments and
# conversations, respectively.
#

from dataclasses import dataclass


@dataclass
class TimeSegment:
    """
    A segment of time, [start,end), in an audio waveform. Units may be milliseconds or sample
    indices.
    """
    start: int
    end: int