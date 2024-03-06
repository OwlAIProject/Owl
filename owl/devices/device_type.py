from enum import Enum, EnumMeta

class DeviceTypeMeta(EnumMeta):
    def __contains__(cls, item):
        # This allows us to test e.g. ("apple_watch" in DeviceType)
        try:
            cls(item)
        except ValueError:
            return False
        return True
    
class DeviceType(Enum, metaclass=DeviceTypeMeta):
    """
    Short-form unique identifiers for supported capture devices. Must be consistent with all client
    software. Names must be usable in filepaths.
    """
    UNKNOWN = "unknown_device"
    IPHONE = "iphone"
    APPLE_WATCH = "apple_watch"
    XIAO_ESP32S3_SENSE = "xiao_esp32s3_sense"
    SONY_SPRESENSE = "spresense"
    WEB = "web"
    ANDROID = "android"