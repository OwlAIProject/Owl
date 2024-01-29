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

    def __init__(self, capture_directory: str, capture_uuid: str, device_type: DeviceType | str, timestamp: str | datetime, file_extension: str):
        """
        Construct the object.

        Parameters
        ----------
        capture_directory : str
            The base capture directory. Files stored as:
            {capture_dir}/{date}/{device}/{timestamp}_{capture_uuid}.{ext}
        capture_uuid : str
            Capture ID. Unique identifier for the capture that is used on the file system and
            internally to the server app.
        device_type : DeviceType | str
            Device type corresponding to DeviceType enum. If not a valid string, DeviceType.UNKNOWN
            will be assigned.
        timestamp : str | datetime
            Timestamp of beginning of capture in format %Y%m%d-%H%M%S.%f (YYYYmmdd-HHMMSS.fff) or as
            a datetime object. If string, caller must ensure it is formatted correctly!
        file_extension : str
            File extension (e.g., "wav"). If not provided, "bin" will be used. Leading '.' (e.g., 
            ".wav") is acceptable (os.path.splitext() produces this) and will be handled correctly.
        """
        self.conversation_segments = {}
        self._capture_directory = capture_directory
        self.capture_uuid = capture_uuid
        if isinstance(device_type, DeviceType):
            self.device_type = device_type
        elif isinstance(device_type, str):
            self.device_type = DeviceType(device_type) if device_type in DeviceType else DeviceType.UNKNOWN
        else:
            raise ValueError("'device_type' must be string or DeviceType")
        
        # Timestamp may be correctly-formatted string or datetime
        if isinstance(timestamp, str):
            # Ensure timestamp is consistent format by internalizing to datetime
            try:
                self.timestamp = datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
            except:
                raise ValueError("'timestamp' string does not conform to YYYYmmdd-HHMMSS.fff format")
        elif isinstance(timestamp, datetime):
            self.timestamp = timestamp
        else:
            raise ValueError("'timestamp' must be string or datetime")
        
        # Strip leading '.' just in case os.path.splitext(), which retains the '.', was used
        file_extension = file_extension.lstrip(".")

        # Filepath: {capture_dir}/{date}/{device}/{timestamp}_{capture_uuid}.{ext}
        dir = os.path.join(capture_directory, self.date_string(), self.device_type.value)
        filename = f"{self.timestamp_string()}_{self.capture_uuid}.{file_extension}"
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

    def create_conversation_segment(self, conversation_uuid: str, timestamp: datetime, file_extension: str) -> CaptureSegmentFile:
        """
        Creates a conversation segment associated with this CaptureFile. The actual underlying file
        will not be created and the caller should use the resulting object's filepath to do so.

        Parameters
        ----------
        conversation_uuid : str
            Unique identifier that will be associated with the conversation and its capture file.
        timestamp : datetime
            Timestamp of the start of this conversation.
        file_extension : str
            File extension of the capture audio file (e.g., "wav", "aac", etc.)

        Returns
        -------
        CaptureSegmentFile
            The CaptureSegmentFile object, which will have been added to the dictionary of segments
            for this capture.
        """
        assert isinstance(timestamp, datetime)

        capture_file = self
        file_extension = file_extension.lstrip(".") # strip leading '.' just in case os.path.splitext() was used
        ext = (file_extension if file_extension else "bin").lstrip(".") # take care to strip leading '.'

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
