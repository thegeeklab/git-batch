#!/usr/bin/env python3
"""Global utility methods and classes."""

import os
import sys
from distutils.util import strtobool


def normalize_path(path):
    if path:
        return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def to_bool(string):
    return bool(strtobool(str(string)))


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
