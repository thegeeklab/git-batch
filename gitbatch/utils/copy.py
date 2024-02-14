"""Copy file utils."""

import shutil
from os import utime
from pathlib import Path


def _coerce_to_path(source, dest):
    return Path(source).resolve(), Path(dest).resolve()


def copy_basic_file_stats(source, dest):
    """
    Copy only the m_time and a_time attributes from source to destination.

    Both are expected to exist. The extended attribute copy has sideeffects
    with SELinux and files copied from temporary directories and copystat
    doesn't allow disabling these copies.
    """
    source, dest = _coerce_to_path(source, dest)
    src_stat = source.stat()
    utime(dest, ns=(src_stat.st_atime_ns, src_stat.st_mtime_ns))


def copy_file_with_basic_stats(source, dest):
    """
    Simplified copy2 to copy extended file attributes.

    Only the access time and modified times are copied as
    extended attribute copy has sideeffects with SELinux and files
    copied from temporary directories.
    """
    source, dest = _coerce_to_path(source, dest)

    shutil.copy(source, dest)
    copy_basic_file_stats(source, dest)
