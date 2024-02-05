#
# async_multiprocessing_queue.py
#
# A wrapper around a multiprocessing.Queue that provides an async interface.
#

import asyncio
from multiprocessing import Queue
from queue import Empty, Full


class AsyncMultiprocessingQueue:
    """
    Async wrapper for multiprocessing.Queue.
    """

    _sleep: float = 0

    def __init__(self, queue: Queue):
        """
        Instantiates an asynchronous interface to a multiprocessing.Queue.

        Parameters
        ----------
        queue: multiprocessing.Queue
            Underlying multiprocessing.Queue to wrap.
        """
        self._q = queue

    async def get(self):
        while True:
            try:
                return self._q.get_nowait()
            except Empty:
                await asyncio.sleep(self._sleep)
    
    async def put(self, item): 
        while True:
            try:
                self._q.put_nowait(item)
                return None
            except Full:
                await asyncio.sleep(self._sleep)

    def task_done(self):
        self._q.task_done()

    def underlying_queue(self) -> Queue:
        return self._q