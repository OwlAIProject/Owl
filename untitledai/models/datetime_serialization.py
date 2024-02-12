#
# datetime_serialization.py
#
# Serialization of datetimes into strings in a standardized way for the server and display clients.
#

from datetime import datetime


def datetime_string(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]