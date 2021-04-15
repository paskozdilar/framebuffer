#!/usr/bin/env python3
"""
This module contains FrameBufferClient implementation of the framebuffer
shared-memory IPC.

Each FrameBufferClient is tied to its key, with which it is initialized.

---

Convenience function `read_frame` is implemented for the single-buffer case.

If you're using multi-buffer reads, this implementation will be EXTREMELY
inefficient because it closes and opens a new buffer every time `key` changes,
so it would be smart to roll your own implementation.
"""

import atexit
import base64
import logging
import pyhash
import sys
from sysv_ipc import SharedMemory


__default_buffer = None


logger = logging.getLogger(__name__)


def read_frame(frame_info: dict) -> bytes:
    """
    Receives `frame_info` dict which must contain the following items:
    {
        "key": <str>,
        "offset": <int>,
        "size": <int>,
        "checksum": <str>,
    }

    If read was successful, returns a bytes blob which contains the JPEG frame.
    Otherwise, raises FrameBufferTimeout.
    """
    global __default_buffer

    key = frame_info['key']
    offset = frame_info['offset']
    size = frame_info['size']
    checksum = frame_info['checksum']

    if __default_buffer is not None and __default_buffer.key != key:
        __default_buffer.stop()
        atexit.unregister(__default_buffer.stop)
        __default_buffer = None

    if __default_buffer is None:
        __default_buffer = FrameBufferClient(key)
        atexit.register(__default_buffer.stop)
        __default_buffer.start()

    return __default_buffer.read(offset, size, checksum)


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
        """ Start shared memory client """
        self.shared_memory = SharedMemory(key=self.key)
        self.buffer = memoryview(self.shared_memory)
        self.size = self.shared_memory.size
        logger.info('Started FrameBufferClient - key=%s, size=%d' \
                    % (self.key, self.size))

    def stop(self):
        """ Stop shared memory client """
        self.shared_memory.detach()
        logger.info('Stopped FrameBufferClient - key=%s, key=%d' \
                    % (self.key, self.size))

    def set_key(self, key):
        """ Set shared memory key (must be done before __enter__/start) """
        self.key = key

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
