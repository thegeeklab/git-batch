"""Default package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("git-batch")
except PackageNotFoundError:
    __version__ = "0.0.0"
