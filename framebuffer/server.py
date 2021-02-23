#!/usr/bin/env python3

import logging
from sysv_ipc import SharedMemory, IPC_CREX


class FrameBufferServer:

    def __init__(self, size: int):
        self.buffer = None
        self.key = None
        self.shared_memory = None
        self.size = size
        self.offset = 0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()

    def start(self):
        self.shared_memory = SharedMemory(key=None, flags=IPC_CREX, size=self.size)
        self.buffer = memoryview(self.shared_memory)
        self.key = self.shared_memory.key
        logging.info(f'Started FrameBufferServer - {self.key=}, {self.size=}')

    def stop(self):
        self.shared_memory.detach()
        self.shared_memory.remove()
        logging.info(f'Stopped FrameBufferServer - {self.key=}, {self.size=}')

    def get_key(self):
        return self.key

    def allocate(self, size: int) -> int:
        """ Allocates a chunk of data and returns offset """
        offset = self.offset
        self.offset = (self.offset + size) % self.size
        return offset
