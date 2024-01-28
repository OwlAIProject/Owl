#
# capture_files.py
#
# A "capture" is a complete end-to-end recording produced by a client device. Captures may contain
# zero or more conversations. As conversations are discovered while the capture is in progress or 
# after it is complete, they are segmented out into their own capture files: capture segments.
#
# The CaptureFile and CaptureSegmentFile objects encapsulate a file's storage location and metadata
# associated with it. Both refer strictly to the audio files themselves and not e.g., transcript or
# conversation JSON files stored alongside. However, the directory structure and filename
# conventions for all of these are defined here.
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
from dataclasses import dataclass
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
import uuid

from ..devices import DeviceType

def _timestamp_string(timestamp: datetime) -> str:
    return timestamp.strftime("%Y%m%d-%H%M%S.%f")[:-3]

@dataclass
class CaptureSegmentFile:
    """
    Encapsulates a file on disk containing a single conversation segmented out from a parent
    capture. These objects must be created via CaptureFile.create_conversation_segment().
    """
    conversation_uuid: str
    timestamp: datetime
    filepath: str

    def _from_filepath(filepath: str) -> CaptureSegmentFile:
        """
        Constructs the object from a capture segment filepath. If the filepath does not appear to be
        the correct type of file, returns None.

        Parameters
        ----------
        filepath : str
            Complete filepath of the capture segment file.

        Returns
        -------
        CaptureSegmentFile | None
            Object or None if unable to reconstruct from filepath.
        """
        if not os.path.isfile(filepath):
            return None
        filename = os.path.basename(filepath)
        rootname, file_extension = os.path.splitext(filename)
        file_parts = rootname.split("_")
        if len(file_parts) != 2:
            return None
        timestamp, conversation_uuid = file_parts
        if len(conversation_uuid) != 32:
            return None
        try:
            datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
        except:
            # Invalid timestamp format
            return None
        return CaptureSegmentFile(
            conversation_uuid=conversation_uuid,
            timestamp=timestamp,
            filepath=filepath
        )

    def timestamp_string(self) -> str:
        return _timestamp_string(timestamp=self.timestamp)

    def get_transcription_filepath(self) -> str:
        """
        Name of the transcript file on disk. Adjacent to this file.

        Returns
        -------
        str
            Filepath of transcript file.
        """
        our_dir = os.path.dirname(self.filepath)
        filename = os.path.basename(self.filepath)
        rootname, _ = os.path.splitext(filename)
        return os.path.join(our_dir, f"{rootname}_transcript.json")

    def get_conversation_filepath(self) -> str:
        """
        Name of the conversation file on disk. Adjacent to this file.

        Returns
        -------
        str
            Filepath of conversation file.
        """
        our_dir = os.path.dirname(self.filepath)
        filename = os.path.basename(self.filepath)
        rootname, _ = os.path.splitext(filename)
        return os.path.join(our_dir, f"{rootname}_conversation.json")

class CaptureFile:
    """
    Encapsulates a file on disk containing a capture. Includes only the limited metadata embedded in
    the filepath and filename so that the object can be created from metadata or from a filepath.

    A capture is a complete recording session. It may generally contain multiple conversations,
    which will be segmented apart.
    """
    capture_uuid: str
    device_type: DeviceType
    timestamp: datetime
    filepath: str
    conversation_segments: Dict[str, CaptureSegmentFile]
    
    def get_capture_uuid(filepath: str) -> str | None:
        """
        Extracts the capture ID from a capture file stored on disk.

        Parameters
        ----------
        filepath : str
            Either a filename of format {timestamp}_{capture_uuid}.{ext} or a complete filepath.
        
        Returns
        -------
        str | None
            The capture ID or None of it is missing/malformed.
        """
        # {timestamp}_{capture_uuid}.{ext} -> {capture_uuid}
        filename = os.path.basename(filepath)
        rootname = os.path.splitext(filename)[0]
        parts = rootname.split("_")
        if len(parts) != 2 or len(parts[1]) != 32:
            return None
        return parts[1]
    
    def from_filepath(filepath: str) -> CaptureFile | None:
        """
        Constructs object from a complete filepath. Must include every path component following the
        base file directory, as capture metadata is sprinkled throughout.

        Parameters
        ----------
        filepath : str
            Full filepath: {capture_dir}/{date}/{device}/{timestamp}_{capture_uuid}.{ext}. The audio
            directory is reconstructed from this path.

        Returns
        -------
        CaptureFile | None
            Object corresponding to the file's metadata or None if insufficient metadata due to 
            filepath having incorrect format.
        """
        path_parts = Path(filepath).parts
        if len(path_parts) < 4:
            return None
        capture_directory = os.path.join(*path_parts[:-3])  # capture base directory excludes last three parts
        device_type = path_parts[-2]
        rootname, file_extension = os.path.splitext(path_parts[-1])
        file_parts = rootname.split("_")
        if len(file_parts) != 2:
            return None
        timestamp, capture_uuid = file_parts
        if len(capture_uuid) != 32:
            return None
        try:
            datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
        except:
            # Invalid timestamp format
            return None
        
        # Create initial object
        capture_file = CaptureFile(
            capture_directory=capture_directory,
            capture_uuid=capture_uuid,
            device_type=device_type,
            timestamp=timestamp,
            file_extension=file_extension
        )

        # Find capture segments
        segment_dir = capture_file._get_capture_segment_directory()
        if os.path.isdir(segment_dir):
            for filename in os.listdir(segment_dir):
                # Try to create the object. If the filepath is incorrectly formatted (i.e., is a 
                # different kind of file in that directory), None will be returned
                filepath = os.path.join(segment_dir, filename)
                segment_file = CaptureSegmentFile._from_filepath(filepath=filepath)
                if segment_file:
                    capture_file.conversation_segments[segment_file.conversation_uuid] = segment_file

        return capture_file

    def __init__(self, capture_directory: str, **kwargs):
        """
        Construct the object.

        Parameters
        ----------
        capture_directory : str
            The base capture directory. Files stored as:
            {capture_dir}/{date}/{device}/{timestamp}_{capture_uuid}.{ext}
        capture_uuid : str | None
            Capture ID. If not specified, a new random ID is assigned.
        device_type : DeviceType | str | None
            Device type corresponding to DeviceType enum. If not a valid string, DeviceType.UNKNOWN
            will be assigned.
        timestamp : str | datetime | None
            Timestamp of beginning of capture in format %Y%m%d-%H%M%S.%f (YYYYmmdd-HHMMSS.fff) or as
            a datetime object. If None or if a string was supplied that could not be parsed,
            datetime.now(timezone.utc) will be used.
        file_extension : str | None
            File extension (e.g., "wav"). If not provided, "bin" will be used.
        """
        self.conversation_segments = {}
        self._capture_directory = capture_directory
        self.capture_uuid = kwargs["capture_uuid"] if "capture_uuid" in kwargs else uuid.uuid1().hex
        self.device_type = kwargs["device_type"] if "device_type" in kwargs else "unknown"
        if isinstance(self.device_type, str):
            self.device_type = DeviceType(self.device_type) if self.device_type in DeviceType else DeviceType.UNKNOWN

        # Timestamp may be correctly-formatted string or datetime
        if "timestamp" in kwargs:
            ts = kwargs["timestamp"]
            if isinstance(ts, str):
                # Ensure timestamp is consistent format by internalizing to datetime
                try:
                    self.timestamp = datetime.strptime(ts, "%Y%m%d-%H%M%S.%f")
                except:
                    #TODO: log error?
                    self.timestamp = datetime.now(timezone.utc)
            elif isinstance(ts, datetime):
                self.timestamp = ts
            else:
                #TODO: log error?
                self.timestamp = datetime.now(timezone.utc)

        # Filepath: {capture_dir}/{date}/{device}/{timestamp}_{capture_uuid}.{ext}
        ext = (kwargs["file_extension"] if "file_extension" in kwargs else "bin").lstrip(".")
        dir = os.path.join(capture_directory, self.date_string(), self.device_type.value)
        filename = f"{self.timestamp_string()}_{self.capture_uuid}.{ext}"
        self.filepath = os.path.join(dir, filename)

        # Create the directory
        os.makedirs(name=dir, exist_ok=True)

    def timestamp_string(self) -> str:
        return _timestamp_string(timestamp=self.timestamp)

    def date_string(self) -> str:
        return self.timestamp.strftime("%Y%m%d")
    
    def _get_capture_segment_directory(self):
        # Store segments in sub-directory {capture_timestamp}_{capture_uuid} alongside parent
        # capture file, i.e., {capture_dir}/{date}/{device}/{capture_timestamp}_{capture_uuid}
        parent_dir = os.path.dirname(self.filepath)
        return os.path.join(parent_dir, f"{self.timestamp_string()}_{self.capture_uuid}")

    def create_conversation_segment(self, timestamp: datetime, conversation_uuid: str = None, file_extension: str = None):
        capture_file = self
        conversation_uuid = conversation_uuid if conversation_uuid else uuid.uuid1().hex
        ext = file_extension if file_extension else "bin"

        # Our file is: {conversation_timestamp}_{conversation_uuid}.{ext}, stored in the segment
        # subdirectory
        our_dir = capture_file._get_capture_segment_directory()
        filename = f"{_timestamp_string(timestamp)}_{conversation_uuid}.{ext}"
        filepath = os.path.join(our_dir, filename)

        # Create the directory
        os.makedirs(name=our_dir, exist_ok=True)

        # Create the object and add it to this capture file object
        segment_file = CaptureSegmentFile(
            conversation_uuid=conversation_uuid,
            timestamp=timestamp,
            filepath=filepath
        )
        capture_file.conversation_segments[conversation_uuid] = segment_file

        return segment_file
