#!/usr/bin/env python3

import datetime
import random
import sys
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer
from framebuffer.client import FrameBufferClient


size = 5 * 2**20  # 5MiB
data = random.getrandbits(8 * size).to_bytes(size, sys.byteorder)

host, port = 'localhost', 8000
buffer_host, buffer_port = 'localhost', 8001
args = sys.argv[1:]


with ServerProxy(f'http://{buffer_host}:{buffer_port}') as buffer_rpc, \
        SimpleXMLRPCServer((host, port)) as server, \
        FrameBufferClient(key=buffer_rpc.get_key()) as client:

    def getData():
        offset = buffer_rpc.allocate(size)
        checksum = client.write(offset, data)
        print(offset, size, checksum)
        return (offset, size, checksum)

    server.register_function(getData)
    print(f'Serving XML-RPC on {host} port {port}', file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nKeyboard interrupt received, exiting.', file=sys.stderr)
        sys.exit(0)
