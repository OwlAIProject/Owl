#
# datetime_serialization.py
#
# Serialization of datetimes into strings in a standardized way for the server and display clients.
#

from datetime import datetime


def timestamp_string(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

def date_string(timestamp: datetime) -> str:
    return timestamp.strftime("%Y%m%d")

def try_parse_timestamp(from_string: str) -> datetime | None:
    try:
        return datetime.strptime(from_string, "%Y%m%d-%H%M%S.%f")
    except:
        return None