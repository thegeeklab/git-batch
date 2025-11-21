"""
Copy file utils.

Provides a copy of the shutil.copytree function and its dependencies.
The copystat function used to preserve extended attributes has side effects
with SELinux in combination with files copied from temporary directories.
"""

import contextlib
import os
import stat
import sys
from collections.abc import Callable
from shutil import Error, copy
from typing import Any

if sys.platform == "win32":
    import _winapi
    from stat import IO_REPARSE_TAG_MOUNT_POINT
else:
    _winapi = None
    IO_REPARSE_TAG_MOUNT_POINT = None


def _islink(fn: os.DirEntry | str) -> bool:
    return fn.is_symlink() if isinstance(fn, os.DirEntry) else os.path.islink(fn)


def _copytree(
    entries: list[os.DirEntry],
    src: str,
    dst: str,
    symlinks: bool,
    ignore: Callable[[str, list[str]], list[str]] | None,
    ignore_dangling_symlinks: bool,
    dirs_exist_ok: bool = False,
) -> str:
    ignored_names = ignore(os.fspath(src), [x.name for x in entries]) if ignore is not None else ()

    os.makedirs(dst, exist_ok=dirs_exist_ok)
    errors = []

    for src_entry in entries:
        if src_entry.name in ignored_names:
            continue
        src_name = os.path.join(src, src_entry.name)
        dst_name = os.path.join(dst, src_entry.name)
        try:
            is_symlink = src_entry.is_symlink()
            if is_symlink and os.name == "nt":
                # Special check for directory junctions, which appear as
                # symlinks but we want to recurse.
                lstat = src_entry.stat(follow_symlinks=False)
                if (
                    IO_REPARSE_TAG_MOUNT_POINT is not None
                    and hasattr(lstat, "st_reparse_tag")
                    and lstat.st_reparse_tag == IO_REPARSE_TAG_MOUNT_POINT
                ):
                    is_symlink = False
            if is_symlink:
                link_to = os.readlink(src_name)
                if symlinks:
                    os.symlink(link_to, dst_name)
                    simple_copy_stat(src_name, dst_name, follow_symlinks=(not symlinks))
                else:
                    if not os.path.exists(link_to) and ignore_dangling_symlinks:
                        continue

                    if src_entry.is_dir():
                        simple_copy_tree(
                            src_name,
                            dst_name,
                            symlinks,
                            ignore,
                            ignore_dangling_symlinks,
                            dirs_exist_ok,
                        )
                    else:
                        simple_copy(src_name, dst_name)
            elif src_entry.is_dir():
                simple_copy_tree(
                    src_name,
                    dst_name,
                    symlinks,
                    ignore,
                    ignore_dangling_symlinks,
                    dirs_exist_ok,
                )
            else:
                # Will raise a SpecialFileError for unsupported file types
                simple_copy(src_name, dst_name)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((src_name, dst_name, str(why)))

    try:
        simple_copy_stat(src, dst)
    except OSError as why:
        # Copying file access times may fail on Windows
        if hasattr(why, "winerror"):
            errors.append((src, dst, str(why)))
    if errors:
        raise Error(errors)
    return dst


def simple_copy_tree(
    src: str,
    dst: str,
    symlinks: bool = False,
    ignore: Callable[[str, list[str]], list[str]] | None = None,
    ignore_dangling_symlinks: bool = False,
    dirs_exist_ok: bool = False,
) -> str:
    with os.scandir(src) as itr:
        entries = list(itr)
    return _copytree(
        entries=entries,
        src=src,
        dst=dst,
        symlinks=symlinks,
        ignore=ignore,
        ignore_dangling_symlinks=ignore_dangling_symlinks,
        dirs_exist_ok=dirs_exist_ok,
    )


def simple_copy_stat(src: os.DirEntry | str, dst: str, *, follow_symlinks: bool = True) -> None:
    def _nop(
        *args: Any, ns: tuple[int, int] | None = None, follow_symlinks: bool | None = None
    ) -> None:
        pass

    # follow symlinks (aka don't not follow symlinks)
    follow = follow_symlinks or not (_islink(src) and os.path.islink(dst))
    if follow:
        # use the real function if it exists
        def lookup(name: str) -> Callable:
            return getattr(os, name, _nop)
    else:
        # use the real function only if it exists
        # *and* it supports follow_symlinks
        def lookup(name: str) -> Callable:
            fn = getattr(os, name, _nop)
            if hasattr(os, "supports_follow_symlinks") and fn in os.supports_follow_symlinks:
                return fn
            return _nop

    if isinstance(src, os.DirEntry):
        st = src.stat(follow_symlinks=follow)
    else:
        st = lookup("stat")(src, follow_symlinks=follow)
    mode = stat.S_IMODE(st.st_mode)
    lookup("utime")(dst, ns=(st.st_atime_ns, st.st_mtime_ns), follow_symlinks=follow)

    with contextlib.suppress(NotImplementedError):
        lookup("chmod")(dst, mode, follow_symlinks=follow)


def simple_copy(src: str, dst: str, *, follow_symlinks: bool = True) -> str:
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    if _winapi is not None:
        # Skip Windows-specific copy flags since they're not available in all Python versions
        with contextlib.suppress(OSError):
            copy(src, dst, follow_symlinks=follow_symlinks)
    else:
        copy(src, dst, follow_symlinks=follow_symlinks)

    simple_copy_stat(src, dst, follow_symlinks=follow_symlinks)
    return dst
