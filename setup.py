#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name="redispyauth-prototype",
    version="0.0.1",
    description="Extension library for additional authentication capabilities via Redis-py client.",
    packages=find_packages(
        include=[
            "redisauth",
        ],
        exclude=["tests", ".github"]
    ),
    url="https://github.com/redis-developer/redispy-entra-prototype",
    author="Redis Inc.",
    author_email="oss@redis.com",
)