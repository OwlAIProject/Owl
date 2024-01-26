#
# capture_file.py
#
# CaptureFile encapsulates an audio capture's storage location and metadata associated with it.
#

from __future__ import annotations 
import os
from datetime import datetime, timezone
from pathlib import Path
import uuid

from ..devices import DeviceType

class CaptureFile:
    """
    Encapsulates a file on disk containing a capture. Includes only the limited metadata embedded in
    the filepath and filename so that the object can be created from metadata or from a filepath.
    """
    capture_id: str
    device_type: DeviceType
    timestamp: datetime
    filepath: str

    def get_capture_id(filepath: str) -> str | None:
        """
        Extracts the capture ID from a capture file stored on disk.

        Parameters
        ----------
        filepath : str
            Either a filename of format {timestamp}_{capture_id}.{ext} or a complete filepath.
        
        Returns
        -------
        str | None
            The capture ID or None of it is missing/malformed.
        """
        # {timestamp}_{capture_id}.{ext} -> {capture_id}
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
            Full filepath: {audio_dir}/{date}/{device}/{timestamp}_{capture_id}.{ext}. The audio
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
        audio_directory = os.path.join(*path_parts[:-3])    # audio base directory excludes last three parts
        device_type = path_parts[-2]
        rootname, file_extension = os.path.splitext(path_parts[-1])
        file_parts = rootname.split("_")
        if len(file_parts) != 2:
            return None
        timestamp, capture_id = file_parts
        if len(capture_id) != 32:
            return None
        try:
            print(timestamp)
            datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
        except:
            # Invalid timestamp format
            return None
        return CaptureFile(
            audio_directory=audio_directory,
            capture_id=capture_id,
            device_type=device_type,
            timestamp=timestamp,
            file_extension=file_extension
        )

    def __init__(self, audio_directory: str, **kwargs):
        """
        Construct the object.

        Parameters
        ----------
        audio_directory : str
            The base audio capture directory. Files stored as:
            {audio_dir}/{date}/{device}/{timestamp}_{capture_id}.{ext}
        capture_id : str | None
            Capture ID. If not specified, a new random ID is assigned.
        device_type : DeviceType | str | None
            Device type corresponding to DeviceType enum. If not a valid string, DeviceType.UNKNOWN
            will be assigned.
        timestamp : str | datetime | None
            Timestamp of beginning of capture in format %Y%m%d-%H%M%S.%f (YYYYmmdd-hhmm.sss) or as a
            datetime object. If None or if a string was supplied that could not be parsed,
            datetime.now(timezone.utc) will be used.
        file_extension : str | None
            File extension (e.g., "wav"). If not provided, "bin" will be used.
        """
        self.capture_id = kwargs["capture_id"] if "capture_id" in kwargs else uuid.uuid1().hex
        self.device_type = kwargs["device_type"] if "device_type" in kwargs else "unknown"
        if isinstance(self.device_type, str):
            self.device_type = DeviceType(self.device_type) if self.device_type in DeviceType else DeviceType.UNKNOWN

        # Timestamp may be correctly-formatted string or struct_time
        if "timestamp" in kwargs:
            ts = kwargs["timestamp"]
            if isinstance(ts, str):
                # Ensure timestamp is consistent format by internalizing to struct_time
                try:
                    self.timestamp = datetime.strptime(ts, "%Y%m%d-%H%M%S.%f")
                except:
                    #TODO: log error
                    self.timestamp = datetime.now(timezone.utc)
            elif isinstance(ts, datetime):
                self.timestamp = ts
            else:
                #TODO: log error
                self.timestamp = datetime.now(timezone.utc)

        # Filepath: {audio_dir}/{date}/{device}/{timestamp}_{capture_id}.{ext}
        ext = (kwargs["file_extension"] if "file_extension" in kwargs else "bin").lstrip(".")
        dir = os.path.join(audio_directory, self.date_string(), self.device_type.value)
        filename = f"{self.timestamp_string()}_{self.capture_id}.{ext}"
        self.filepath = os.path.join(dir, filename)

        # Create the directory
        os.makedirs(name=dir, exist_ok=True)

    def timestamp_string(self) -> str:
        return self.timestamp.strftime("%Y%m%d-%H%M%S.%f")[:-3] # millisecond resolution

    def date_string(self) -> str:
        return self.timestamp.strftime("%Y%m%d")
    


    