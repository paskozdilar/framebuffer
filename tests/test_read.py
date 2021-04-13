#!/usr/bin/env python3

import logging
import random
import sys

import pytest

from framebuffer.server import FrameBufferServer
from framebuffer.client import FrameBufferClient, FrameBufferTimeout


buffer_size = 2**20
messages = 10


def _random_bytes(size):
    return random.getrandbits(8*size).to_bytes(length=size, byteorder=sys.byteorder)


def test_basic_read():
    with FrameBufferServer(buffer_size) as server, \
            FrameBufferClient(server.get_key()) as client:

        size = buffer_size
        data = _random_bytes(size)
        offset = server.allocate(size)
        checksum = client.write(offset, data)

        read_data = client.read(offset=offset, size=size, checksum=checksum)

        assert data == read_data


def test_timeout():
    with FrameBufferServer(buffer_size) as server, \
            FrameBufferClient(server.get_key()) as client:

        size = buffer_size // messages

        # Write almost till the end of the buffer
        frame_infos = []
        for _ in range(messages):
            data = _random_bytes(size)
            offset = server.allocate(size)
            checksum = client.write(offset, data)
            frame_info = {
                'data': data,
                'offset': offset,
                'size': size,
                'checksum': checksum,
            }
            frame_infos.append(frame_info)

        for frame_info in frame_infos:
            data, offset, size, checksum = (frame_info[key]
                                            for key in ('data', 'offset', 'size', 'checksum'))
            read_data = client.read(offset=offset, size=size, checksum=checksum)
            assert data == read_data

        # Add another write and assert first_frame_info doesn't work anymore
        data = _random_bytes(size)
        offset = server.allocate(size)
        client.write(offset, data)

        offset = frame_infos[0]['offset']
        size = frame_infos[0]['size']
        checksum = frame_infos[0]['checksum']

        with pytest.raises(FrameBufferTimeout):
            read_data = client.read(offset=offset, size=size, checksum=checksum)
