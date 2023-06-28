#!/usr/bin/env python3
"""Global utility methods and classes."""

import os
from distutils.util import strtobool
from typing import ClassVar


def normalize_path(path):
    if path:
        return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))

    return None


def to_bool(string):
    return bool(strtobool(str(string)))


class Singleton(type):
    """Meta singleton class."""

    _instances: ClassVar[dict] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
