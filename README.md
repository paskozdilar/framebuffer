# core-framebuffer

Minimalistic SharedMemory-based framebuffer Python library for fast data
transfer between processes/containers.


## Concept:

This concept assumes a single service that holds all the shared memory
instances (and is properly configured to release the shared memory on exit,
handle interrupt signals, etc):

```
                     /----------\                                              
                    /    RING    \                                             
                    \   BUFFER   /                                             
                     \----------/                                              
                           ^                                                   
                           |                                                   
                           |   (1: manage ring buffer and allocate chunks)
                           |                                                   
                 +--------------------+                                             
                 | FRAMEBUFFER SERVER |                                
                 +--------------------+                                
                           ^
                           |       (2: acquire ring buffer - r/w to all)
                           |       (3: request allocation of size N - get offset as response)
                           |
    +-----------+    +-----------+
    | Service_2 |    | Service_1 |
    +-----------+    +-----------+
          ^             |
          |             |   (3: send message with offset, size and checksum as payload)
          +-------------+

    (4: recipient fetches data in the ring buffer and verifies the checksum)
    [on invalid checksum, raises TimeoutError]
```

## API:

Module/class/method tree:

- framebuffer
    - client
        - FrameBufferTimeout(Exception)
        - FrameBufferClient(key: str)
            - start()  <==>  __enter__()
            - stop()   <==>  __exit__()
            - write(offset: int, data: bytes) -> checksum: bytes
            - read(offset: int, size: int, checksum: bytes) -> data: bytes
                                                            -> raise FrameBufferTimeout
    - server
        - FrameBufferServer(key, size)
            - start()  <==>  __enter__()
            - stop()   <==>  __exit__()
            - get_key() -> key: str
            - allocate(size: int) -> offset: str


## Examples:

### Server side:

```python3
import uuid
from framebuffer.server import FrameBufferServer
from __SOME_LIBRARY__ import RPC_METHOD


key = str(uuid.uuid4())
size = 500 * 2**20  # use 500MiB RAM
server = FrameBufferServer(key, size)

with server:
    # example service code...

    @RPC_METHOD(service_name='framebuffer')
    def get_key():
        """ Get shared memory access key """
        return key 

    @RPC_METHOD(service_name='framebuffer')
    def allocate(size):
        """ Allocate buffer of size `size` """
        offset = server.allocate(size)
        return offset

    service.run()
```

### Client side:

Writer:

```python3
from random import getrandbits
frim sys import byteorder

from framebuffer.client import FrameBufferClient
from __SOME_LIBRARY__ import RPC_CALL

# Generate random bytes
size = 2**20
data = getrandbits(8 * size).to_bytes(size, byteorder)

key = RPC_CALL(service_name='framebuffer', 'get_key')

with FrameBufferClient(key) as client:

    # Allocate 1MiB buffer
    offset = RPC_CALL(service_name='framebuffer', 'allocate', args=(size))
    
    # Write data to chunk
    checksum = client.write(offset, data)

    # Send data to service
    RPC_CALL(service_name='reader', 'send_data', args=(offset, size, checksum))
```

Reader:

```python3
from __SOME_LIBRARY__ import SERVICE, RPC_METHOD, RPC_CALL
from framebuffer.client import FrameBufferClient, FrameBufferTimeout

key = RPC_CALL(service_name='framebuffer', 'get_key')

with FrameBufferClient(key) as client:

    @RPC_METHOD(service_name='reader')
    def send_data(offset, size, checksum):
        try:
            data = client.read(offset, size, checksum)
        except FrameBufferTimeout:
            ...
            # handle message timeout...
```

---

## Troubleshooting:

### Docker:

Shared memory is part of the
[IPC](https://man7.org/linux/man-pages/man7/ipc_namespaces.7.html)
[namespace](https://man7.org/linux/man-pages/man7/namespaces.7.html)
inside the kernel.  By default, Docker creates a unique IPC namespace for each
running container.

For this library to work between containers, all containers need to be using
the same IPC namespace. Using `host` IPC namespace might be useful for
communication through normal user processes (e.g. monitoring data flow with a
CLI tool), but provides less isolation as any other process can potentially
attach itself to the same segment of the shared memory, if it knows the right
key.
