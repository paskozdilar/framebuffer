#!/usr/bin/env python3

import base64
import logging
import pyhash
import sys
from sysv_ipc import SharedMemory


class FrameBufferClient:

    def __init__(self, key: str):
        self.buffer = None
        self.key = key
        self.shared_memory = None
        self.size = None
        self._hasher = pyhash.t1ha0()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()

    def start(self):
        self.shared_memory = SharedMemory(key=self.key)
        self.buffer = memoryview(self.shared_memory)
        self.size = self.shared_memory.size
        logging.info('Started FrameBufferClient - %s, %d' % (self.key, self.size))

    def stop(self):
        self.shared_memory.detach()
        logging.info('Stopped FrameBufferClient - %s, %d' % (self.key, self.size))

    def write(self, offset: int, data: bytes) -> str:
        """ Returns `checksum` """
        bytes_to_back = min(len(data), self.size - offset)
        bytes_to_front = len(data) - bytes_to_back
        self.buffer[offset : offset + bytes_to_back] = data[0:bytes_to_back]
        if bytes_to_front > 0:
            self.buffer[0 : bytes_to_front] = data[bytes_to_back:]
        _hash = base64.b64encode(self._hasher(data).to_bytes(8, sys.byteorder)).decode()
        return _hash

    def read(self, offset: int, size: int, checksum: str) -> bytes:
        """ Raises `FrameBufferTimeout` on invalid checksum """
        bytes_from_back = min(size, self.size - offset)
        bytes_from_front = size - bytes_from_back
        data = bytes(self.buffer[offset:offset+bytes_from_back])
        if bytes_from_front > 0:
            data += bytes(self.buffer[0:bytes_from_front])
        _hash = base64.b64encode(self._hasher(data).to_bytes(8, sys.byteorder)).decode()
        if _hash != checksum:
            raise FrameBufferTimeout("Invalid checksum - buffer already reused")
        return data


class FrameBufferTimeout(Exception):
    pass
