#
# datetime_serialization.py
#
# Serialization of datetimes into strings in a standardized way for the server and display clients.
# This is only intended for serializing database objects and not e.g., the capture directory, which
# uses a different format.
#
# TODO:
# -----
# - We should probably standardize on %Y%m%d-%H%M%S.%f, like the capture files, instead.
#

from datetime import datetime


def datetime_string(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]