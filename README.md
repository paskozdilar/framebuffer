# core-framebuffer

Minimalistic SharedMemory-based framebuffer Python library for fast data
transfer between processes/containers.

## Usage:

- instantiate `framebuffer.server.FrameBufferServer` with total segment `size`
  capacity to create the shared memory segment
- call `get_key()` on server to get client `key`
- call `allocate(size)` on server with needed message `size` in bytes to get an
  `offset` to read from/write to
- instantiate `framebuffer.client.FrameBufferClient` (in the same or different
  process) with client `key` to attach to the shared memory segment
- call `write(offset, data)` with `offset` from the allocation call and `data`
  (which must be at most `size` bytes) to write into the shared memory
  segment, and get `checksum`
- call `read(offset, size, checksum)` with previously mentioned `offset`,
  `size`, and `checksum` to attempt to read from shared memory segment,
  and to either get `data` or raise `FrameBufferTimeout`



with the client `key`, and call `read(offset, size


## API:

Module/class/method tree:

- framebuffer
    - client
        - FrameBufferTimeout(Exception)
        - FrameBufferClient(key: str)
            - start()  <==>  __enter__()
            - stop()   <==>  __exit__()
            - write(offset: int, data: bytes) -> checksum: str
            - read(offset: int, size: int, checksum: str) -> data: bytes
                                                          -> raise FrameBufferTimeout
    - server
        - FrameBufferServer(size: int)
            - start()  <==>  __enter__()
            - stop()   <==>  __exit__()
            - get_key() -> key: str
            - allocate(size: int) -> offset: str


## Examples:

### Server side:

```python3
from framebuffer.server import FrameBufferServer
from __SOME_LIBRARY__ import RUN_SERVICE, RPC_METHOD


size = 500 * 2**20  # use 500MiB RAM
server = FrameBufferServer(size)

with server:
    # example service code...

    @RPC_METHOD(service_name='framebuffer')
    def get_key():
        """ Get shared memory access key """
        return server.get_key()

    @RPC_METHOD(service_name='framebuffer')
    def allocate(size):
        """ Allocate buffer of size `size` """
        offset = server.allocate(size)
        return offset

    RUN_SERVICE()
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
from __SOME_LIBRARY__ import RUN_SERVICE, RPC_METHOD
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

    RUN_SERVICE()
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
