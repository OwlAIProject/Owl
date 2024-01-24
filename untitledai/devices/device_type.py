from enum import Enum

class DeviceType(Enum):
    """
    Short-form unique identifiers for supported capture devices. Must be consistent with all client
    software.
    """
    UNKNOWN = "unknown_device"
    IPHONE = "iphone"
    APPLE_WATCH = "apple_watch"
    XIAO_ESP32S3_SENSE = "xiao_esp32s3_sense"
    SONY_SPRESENSE = "spresense"