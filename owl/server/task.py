#
# task.py
#
# Abstract base class for a background server task. These are held in a queue in the AppState
# object.
#

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:   # see: https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
    from .app_state import AppState


class Task(ABC):
    @abstractmethod
    async def run(self, app_state: AppState):
        pass