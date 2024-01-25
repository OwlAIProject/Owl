import os
import datetime
import time
import uuid

from ...devices import DeviceType

class CaptureSession:
    session_id: str
    device_type: DeviceType
    timestamp: time.struct_time
    filepath: str

    def __init__(self, audio_directory: str, **kwargs):
        self.session_id = kwargs["session_id"] if "session_id" in kwargs else uuid.uuid1().hex
        self.device_type = kwargs["device_type"] if "device_type" in kwargs else DeviceType.UNKNOWN

        # Timestamp may be correctly-formatted string or struct_time
        if "timestamp" in kwargs:
            ts = kwargs["timestamp"]
            if isinstance(ts, str):
                # Ensure timestamp is consistent format by internalizing to struct_time
                try:
                    self.timestamp = datetime.datetime.strptime(ts, "%Y%m%d-%H%M%S").timetuple()
                except:
                    #TODO: log error
                    self.timestamp = time.localtime()
            elif isinstance(ts, time.struct_time):
                self.timestamp = ts
            else:
                #TODO: log error
                self.timestamp = time.localtime()

        # Filepath: {capture_dir}/{date}/{device}/{timestamp}_{session_id}.{ext}
        ext = (kwargs["file_extension"] if "file_extension" in kwargs else "bin").lstrip(".")
        dir = os.path.join(audio_directory, self.date_string(), self.device_type.value)
        filename = f"{self.timestamp_string()}_{self.session_id}.{ext}"
        self.filepath = os.path.join(dir, filename)

        # Create the directory
        os.makedirs(name=dir, exist_ok=True)

    def timestamp_string(self) -> str:
        return time.strftime("%Y%m%d-%H%M%S", self.timestamp)

    def date_string(self) -> str:
        return time.strftime("%Y%m%d", self.timestamp)
    


    