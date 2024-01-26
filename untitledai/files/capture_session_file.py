#
# capture_session_file.py
#
# CaptureSessionFile encapsulates a captured audio session's storage location and metadata
# associated with the session.
#

from __future__ import annotations 
import os
from datetime import datetime
from pathlib import Path
import uuid

from ..devices import DeviceType

class CaptureSessionFile:
    """
    Encapsulates a file on disk containing a capture session. Includes only the limited metadata
    embedded in the filepath and filename so that the object can be created from metadata or from a
    filepath.
    """
    session_id: str
    device_type: DeviceType
    timestamp: datetime
    filepath: str

    def get_session_id(filepath: str) -> str | None:
        """
        Extracts the session ID from a capture file stored on disk.

        Parameters
        ----------
        filepath : str
            Either a filename of format {timestamp}_{session_id}.{ext} or a complete filepath.
        
        Returns
        -------
        str | None
            The session ID or None of it is missing/malformed.
        """
        # {timestamp}_{session_id}.{ext} -> {sesion_id}
        filename = os.path.basename(filepath)
        rootname = os.path.splitext(filename)[0]
        parts = rootname.split("_")
        if len(parts) != 2 or len(parts[1]) != 32:
            return None
        return parts[1]
    
    def from_filepath(filepath: str) -> CaptureSessionFile | None:
        """
        Constructs object from a complete filepath. Must include every path component following the
        base file directory, as session metadata is sprinkled throughout.

        Parameters
        ----------
        filepath : str
            Full filepath: {audio_dir}/{date}/{device}/{timestamp}_{session_id}.{ext}. The audio
            directory is reconstructed from this path.

        Returns
        -------
        CaptureSessionFile | None
            Object corresponding to the file's metadata or None if insufficient metadata due to 
            filepath having incorrect format.
        """
        path_parts = Path(filepath).parts
        if len(path_parts) < 4:
            print("1")
            return None
        audio_directory = os.path.join(*path_parts[:-3])    # audio base directory excludes last three parts
        device_type = path_parts[-2]
        rootname, file_extension = os.path.splitext(path_parts[-1])
        file_parts = rootname.split("_")
        if len(file_parts) != 2:
            print("2")
            return None
        timestamp, session_id = file_parts
        if len(session_id) != 32:
            print("3")
            return None
        try:
            print(timestamp)
            datetime.strptime(timestamp, "%Y%m%d-%H%M%S.%f")
        except:
            # Invalid timestamp format
            print("4")
            return None
        return CaptureSessionFile(
            audio_directory=audio_directory,
            session_id=session_id,
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
            {audio_dir}/{date}/{device}/{timestamp}_{session_id}.{ext}
        session_id : str | None
            Session ID. If not specified, a new random ID is assigned.
        device_type : DeviceType | str | None
            Device type corresponding to DeviceType enum. If not a valid string, DeviceType.UNKNOWN
            will be assigned.
        timestamp : str | datetime | None
            Timestamp of beginning of session in format %Y%m%d-%H%M%S.%f (YYYYmmdd-hhmm.sss) or as a
            datetime object. If None or if a string was supplied that could not be parsed,
            datetime.now() will be used.
        file_extension : str | None
            File extension (e.g., "wav"). If not provided, "bin" will be used.
        """
        self.session_id = kwargs["session_id"] if "session_id" in kwargs else uuid.uuid1().hex
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
                    self.timestamp = datetime.now()
            elif isinstance(ts, datetime):
                self.timestamp = ts
            else:
                #TODO: log error
                self.timestamp = datetime.now()

        # Filepath: {audio_dir}/{date}/{device}/{timestamp}_{session_id}.{ext}
        ext = (kwargs["file_extension"] if "file_extension" in kwargs else "bin").lstrip(".")
        dir = os.path.join(audio_directory, self.date_string(), self.device_type.value)
        filename = f"{self.timestamp_string()}_{self.session_id}.{ext}"
        self.filepath = os.path.join(dir, filename)

        # Create the directory
        os.makedirs(name=dir, exist_ok=True)

    def timestamp_string(self) -> str:
        return self.timestamp.strftime("%Y%m%d-%H%M%S.%f")[:-3] # millisecond resolution

    def date_string(self) -> str:
        return self.timestamp.strftime("%Y%m%d")
    


    