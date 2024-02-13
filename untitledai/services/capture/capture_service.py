#
# capture_service.py
#
# Manages capture file and capture segment (conversation) references. These are stored in the data-
# base so that state can always be recovered.
#

from datetime import datetime
import logging
import os

from ...database.database import Database
from ...core.config import Configuration
from ...devices import DeviceType
from ...models.schemas import Capture
from ...database.crud import create_capture_file_ref, get_capture_file_ref
from ...files import CaptureDirectory

logger = logging.getLogger(__name__)

class CaptureService:
    def __init__(self, config: Configuration, database: Database):
        self._config = config
        self._database = database
    
    def create_capture_file(self, capture_uuid: str, format: str, start_time: datetime, device_type: DeviceType | str) -> Capture:
        with next(self._database.get_db()) as db:
            # This method is only for creating new captures
            existing_capture_file_ref = get_capture_file_ref(db=db, capture_uuid=capture_uuid)
            assert existing_capture_file_ref is None

            # Parse device type
            assert isinstance(device_type, DeviceType) or isinstance(device_type, str)
            device: DeviceType = None
            if isinstance(device_type, str):
                device = DeviceType(device_type) if device_type in DeviceType else DeviceType.UNKNOWN
            else:
                device = device_type

            # Create and enter into database
            new_capture_file = Capture(
                capture_uuid=capture_uuid,
                filepath=CaptureDirectory(config=self._config).get_capture_filepath(capture_uuid=capture_uuid, format=format, start_time=start_time, device_type=device),
                device_type=device.value,
                start_time=start_time
            )
            saved_capture_file = create_capture_file_ref(db, new_capture_file)

            return saved_capture_file
        
    def get_capture_file(self, capture_uuid: str) -> Capture | None:
        with next(self._database.get_db()) as db:
            return get_capture_file_ref(db=db, capture_uuid=capture_uuid)