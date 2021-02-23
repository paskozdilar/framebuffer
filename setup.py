#!/usr/bin/env python3

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="framebuffer",
    version="0.1.0",
    author="Pasko Zdilar",
    author_email="paskozdilar@gmail.com",
    description="SharedMemory-based frame buffer client/server library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paskozdilar/framebuffer",
    packages=setuptools.find_packages(exclude=['examples']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "pyhash",
        "sysv_ipc",
    ],
    python_requires='>=3.6',
)

