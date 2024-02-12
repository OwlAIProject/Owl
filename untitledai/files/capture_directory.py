#
# capture_directory.py
#
# Functions for creating directories and filepaths on disk in the capture storage directory.
#
# A "capture" is a complete end-to-end recording produced by a client device. Captures may contain
# zero or more conversations. As conversations are discovered while the capture is in progress or
# after it is complete, they are segmented out into their own capture segment files.
#
# Capture directory structure:
#
#   {capture_dir}/
#       {date}/
#           {device}/
#               {capture_timestamp}_{capture_uuid}.{ext} <-- complete capture audio file
#               {capture_timestamp}_{capture_uuid}/      <-- capture segments (conversations) directory
#                   {conversation1_timestamp}_{conversation1_uuid}.{ext}
#                   {conversation1_timestamp}_{conversation1_uuid}_transcript.json      <-- transcript
#                   {conversation1_timestamp}_{conversation1_uuid}_conversation.json    <-- conversation
#                   ...
#                   {conversation2_timestamp}_{conversation2_uuid}.{ext}
#                   {conversation2_timestamp}_{conversation2_uuid}_transcript.json
#                   {conversation2_timestamp}_{conversation2_uuid}_conversation.json
#
# Timestamp format: YYYYYmmdd-HHMMSS.fff (millisecond resolution).
#

from __future__ import annotations
import os
from datetime import datetime

from ..core.config import Configuration
from ..devices import DeviceType
from ..models.schemas import CaptureFileRef, CaptureSegmentFileRef
from ..models.datetime_serialization import timestamp_string, date_string


class CaptureDirectory:
    def __init__(self, config: Configuration):
        self._config = config

    def get_capture_filepath(self, capture_uuid: str, format: str, start_time: datetime, device_type: DeviceType) -> str:
        file_extension = format

        # Filepath: {capture_dir}/{date}/{device}/{timestamp}_{capture_uuid}.{ext}
        dir = os.path.join(self._config.captures.capture_dir, date_string(timestamp=start_time), device_type.value)
        filename = f"{timestamp_string(timestamp=start_time)}_{capture_uuid}.{file_extension}"
        filepath = os.path.join(dir, filename)

        # Create the directory
        os.makedirs(name=dir, exist_ok=True)

        return filepath

    def get_capture_segment_filepath(self, capture_file: CaptureFileRef, conversation_uuid: str, timestamp: datetime) -> str:
        # Same format as parent capture, based on file extension
        format = os.path.splitext(capture_file.file_path)[1].lstrip(".")

        # Our file is: {conversation_timestamp}_{conversation_uuid}.{ext}, stored in the segment
        # subdirectory
        our_dir = self.get_capture_segment_directory(capture_file=capture_file)
        filename = f"{timestamp_string(timestamp)}_{conversation_uuid}.{format}"
        filepath = os.path.join(our_dir, filename)

        # Create the directory
        os.makedirs(name=our_dir, exist_ok=True)

        return filepath

    def get_capture_segment_directory(self, capture_file: CaptureFileRef):
        # Store segments in sub-directory {capture_timestamp}_{capture_uuid} alongside parent
        # capture file, i.e., {capture_dir}/{date}/{device}/{capture_timestamp}_{capture_uuid}
        parent_dir = os.path.dirname(capture_file.file_path)
        return os.path.join(parent_dir, f"{timestamp_string(capture_file.start_time)}_{capture_file.capture_uuid}")

    def get_transcription_filepath(self, segment_file: CaptureSegmentFileRef) -> str:
        """
        Name of the transcript file on disk. Adjacent to the segment file.

        Parameters
        ----------
        segment_file : CatureSegmentFileRef
            The capture segment file containing the conversation.

        Returns
        -------
        str
            Filepath of transcript file.
        """
        our_dir = os.path.dirname(segment_file.file_path)
        filename = os.path.basename(segment_file.file_path)
        rootname, _ = os.path.splitext(filename)
        return os.path.join(our_dir, f"{rootname}_transcript.json")

    def get_conversation_filepath(self, segment_file: CaptureSegmentFileRef) -> str:
        """
        Name of the conversation file on disk. Adjacent to the segment file.

        Parameters
        ----------
        segment_file : CatureSegmentFileRef
            The capture segment file containing the conversation.

        Returns
        -------
        str
            Filepath of conversation file.
        """
        our_dir = os.path.dirname(segment_file.file_path)
        filename = os.path.basename(segment_file.file_path)
        rootname, _ = os.path.splitext(filename)
        return os.path.join(our_dir, f"{rootname}_conversation.json")
