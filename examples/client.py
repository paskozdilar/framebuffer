#!/usr/bin/env python3

import datetime
import random
import sys
import time
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer
from framebuffer.client import FrameBufferClient, FrameBufferTimeout


host, port = 'localhost', 8000
buffer_host, buffer_port = 'localhost', 8001
args = sys.argv[1:]


with ServerProxy('http://%s:%d' % (buffer_host, buffer_port)) as buffer_rpc, \
        ServerProxy('http://%s:%d' % (host, port)) as server_rpc, \
        FrameBufferClient(key=buffer_rpc.get_key()) as client:

    def get_frame():
        try:
            offset, size, checksum = server_rpc.getData()
            data = client.read(offset, size, checksum)
            return data
        except FrameBufferTimeout as exc:
            print('%s: %s' % (type(exc).__name__, str(exc)), file=sys.stderr)

    try:
        print('starting...')
        time.sleep(1)
        end_time = time.time()
        while True:
            start_time = end_time
            total_size = 0
            for _ in range(100):
                frame = get_frame()
                total_size += len(frame)
            end_time = time.time()
            throughput = (total_size / (end_time - start_time)) / (2**20)
            print('Throughput [MiB/s]: %f' % (throughput), file=sys.stderr)

    except KeyboardInterrupt:
        print('\nKeyboard interrupt received, exiting.', file=sys.stderr)
        sys.exit(0)

