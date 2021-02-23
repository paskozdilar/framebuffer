#!/usr/bin/env python3

import datetime
import random
import sys
import uuid
from xmlrpc.server import SimpleXMLRPCServer
from framebuffer.server import FrameBufferServer


key = str(uuid.uuid4())
size = 500 * 2**20  # 500MB
host, port = 'localhost', 8001
args = sys.argv[1:]


with SimpleXMLRPCServer((host, port)) as server, FrameBufferServer(size) as framebuffer:
    server.register_function(framebuffer.get_key)
    server.register_function(framebuffer.allocate)

    print(f'Serving XML-RPC FrameBufferServer on {host} port {port}', file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.", file=sys.stderr)
        sys.exit(0)

