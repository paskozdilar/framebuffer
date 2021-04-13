#!/usr/bin/env python3

import contextlib
import multiprocessing
import subprocess
import time

import pytest

from framebuffer.server import FrameBufferServer
from framebuffer.client import FrameBufferClient


# Use 1 MiB buffers for testing
buffer_size = 2**20


def _get_shmids():
    return set(map(int, subprocess.run(['bash', '-c',
            'ipcs --shmem | grep \'^0x\' | awk \'{print $2}\' | sort -n'
    ], stdout=subprocess.PIPE).stdout.decode().strip().split()))


def _remove_shm(shmid):
    subprocess.run(['bash', '-c', 'ipcrm --shmem-id ' + str(shmid)])


def test_shm_cleanup():
    """
    Test whether server properly cleans up its shared memory segment after
    it's stopped.
    """
    shmids_before = _get_shmids()
    with FrameBufferServer(buffer_size):
        shmids_during = _get_shmids()
    shmids_after = _get_shmids()

    assert shmids_before == shmids_after
    assert shmids_before != shmids_during
    assert len(shmids_during - shmids_before) == 1


def test_shm_cleanup_client():
    """
    Test whether server properly cleans up its shared memory segment after
    client has cleanly stopped.
    """
    shmids_before = _get_shmids()
    with FrameBufferServer(buffer_size) as server, FrameBufferClient(server.get_key()):
        shmids_during = _get_shmids()
    shmids_after = _get_shmids()

    assert shmids_before == shmids_after
    assert shmids_before != shmids_during
    assert len(shmids_during - shmids_before) == 1


def test_shm_cleanup_client_hang():
    """
    Test whether server properly cleans up its shared memory segment if
    client doesn't disconnect explicitely.
    """

    shmids_before = _get_shmids()

    with FrameBufferServer(buffer_size) as server:

        def _run_client():
            client = FrameBufferClient(server.get_key())
            client.start()

        p = multiprocessing.Process(target=_run_client)
        p.start()
        p.join()

        shmids_during = _get_shmids()

    shmids_after = _get_shmids()

    assert shmids_before == shmids_after
    assert shmids_before != shmids_during
    assert len(shmids_during - shmids_before) == 1


def test_shm_cleanup_client_kill():
    """
    Test whether server properly cleans up its shared memory segment after
    client is abruptly terminated.
    """

    client_event = multiprocessing.Event()
    shutdown_event = multiprocessing.Event()

    shmids_before = _get_shmids()
    with FrameBufferServer(buffer_size) as server:

        def _run_client():
            client = FrameBufferClient(server.get_key())
            client.start()
            client_event.set()
            shutdown_event.wait()  # this one will never come :)

        p = multiprocessing.Process(target=_run_client)
        p.start()
        client_event.wait()
        p.kill()
        p.join()
        shmids_during = _get_shmids()
    shmids_after = _get_shmids()

    assert shmids_before == shmids_after
    assert shmids_before != shmids_during
    assert len(shmids_during - shmids_before) == 1


def test_shm_cleanup_server_hang():
    """
    Test whether client properly cleans up its shared memory segment after
    server.
    """
    client_event = multiprocessing.Event()
    shutdown_event = multiprocessing.Event()

    shmids_before = _get_shmids()

    with FrameBufferServer(buffer_size) as server:

        def _run_client():
            client = FrameBufferClient(server.get_key())
            client.start()
            client_event.set()
            shutdown_event.wait()
            client.stop()

        p = multiprocessing.Process(target=_run_client)
        p.start()
        client_event.wait()

    shmids_during = _get_shmids()

    shutdown_event.set()
    p.join()

    shmids_after = _get_shmids()

    assert shmids_before == shmids_after
    assert shmids_before != shmids_during
    assert len(shmids_during - shmids_before) == 1



def test_shm_cleanup_server_hang_client_kill():
    """
    Test whether client properly cleans up its shared memory segment after
    server if it's killed.
    """
    client_event = multiprocessing.Event()
    shutdown_event = multiprocessing.Event()

    shmids_before = _get_shmids()

    with FrameBufferServer(buffer_size) as server:

        def _run_client():
            client = FrameBufferClient(server.get_key())
            client.start()
            client_event.set()
            shutdown_event.wait()
            client.stop()

        p = multiprocessing.Process(target=_run_client)
        p.start()
        client_event.wait()

    shmids_during = _get_shmids()

    p.kill()
    p.join()

    shmids_after = _get_shmids()

    assert shmids_before == shmids_after
    assert shmids_before != shmids_during
    assert len(shmids_during - shmids_before) == 1
