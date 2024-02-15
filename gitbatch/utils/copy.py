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
from shutil import Error, copy

if sys.platform == "win32":
    import _winapi
else:
    _winapi = None


def _islink(fn):
    return fn.is_symlink() if isinstance(fn, os.DirEntry) else os.path.islink(fn)


def _copytree(
    entries,
    src,
    dst,
    symlinks,
    ignore,
    ignore_dangling_symlinks,
    dirs_exist_ok=False,
):
    ignored_names = ignore(os.fspath(src), [x.name for x in entries]) if ignore is not None else ()

    os.makedirs(dst, exist_ok=dirs_exist_ok)
    errors = []

    for srcentry in entries:
        if srcentry.name in ignored_names:
            continue
        srcname = os.path.join(src, srcentry.name)
        dstname = os.path.join(dst, srcentry.name)
        try:
            is_symlink = srcentry.is_symlink()
            if is_symlink and os.name == "nt":
                # Special check for directory junctions, which appear as
                # symlinks but we want to recurse.
                lstat = srcentry.stat(follow_symlinks=False)
                if lstat.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT:
                    is_symlink = False
            if is_symlink:
                linkto = os.readlink(srcname)
                if symlinks:
                    os.symlink(linkto, dstname)
                    simplecopystat(srcname, dstname, follow_symlinks=(not symlinks))
                else:
                    if not os.path.exists(linkto) and ignore_dangling_symlinks:
                        continue

                    if srcentry.is_dir():
                        simplecopytree(
                            srcname,
                            dstname,
                            symlinks,
                            ignore,
                            ignore_dangling_symlinks,
                            dirs_exist_ok,
                        )
                    else:
                        simplecopy(srcname, dstname)
            elif srcentry.is_dir():
                simplecopytree(
                    srcname,
                    dstname,
                    symlinks,
                    ignore,
                    ignore_dangling_symlinks,
                    dirs_exist_ok,
                )
            else:
                # Will raise a SpecialFileError for unsupported file types
                simplecopy(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((srcname, dstname, str(why)))

    try:
        simplecopystat(src, dst)
    except OSError as why:
        # Copying file access times may fail on Windows
        if getattr(why, "winerror", None) is None:
            errors.append((src, dst, str(why)))
    if errors:
        raise Error(errors)
    return dst


def simplecopytree(
    src,
    dst,
    symlinks=False,
    ignore=None,
    ignore_dangling_symlinks=False,
    dirs_exist_ok=False,
):
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


def simplecopystat(src, dst, *, follow_symlinks=True):
    def _nop(*args, ns=None, follow_symlinks=None):  # noqa
        pass

    # follow symlinks (aka don't not follow symlinks)
    follow = follow_symlinks or not (_islink(src) and os.path.islink(dst))
    if follow:
        # use the real function if it exists
        def lookup(name):
            return getattr(os, name, _nop)
    else:
        # use the real function only if it exists
        # *and* it supports follow_symlinks
        def lookup(name):
            fn = getattr(os, name, _nop)
            if fn in os.supports_follow_symlinks:
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


def simplecopy(src, dst, *, follow_symlinks=True):
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    if hasattr(_winapi, "CopyFile2"):
        src_ = os.fsdecode(src)
        dst_ = os.fsdecode(dst)
        flags = _winapi.COPY_FILE_ALLOW_DECRYPTED_DESTINATION  # for compat
        if not follow_symlinks:
            flags |= _winapi.COPY_FILE_COPY_SYMLINK
        try:
            _winapi.CopyFile2(src_, dst_, flags)
            return dst
        except OSError as exc:
            if exc.winerror == _winapi.ERROR_PRIVILEGE_NOT_HELD and not follow_symlinks:
                # Likely encountered a symlink we aren't allowed to create.
                # Fall back on the old code
                pass
            elif exc.winerror == _winapi.ERROR_ACCESS_DENIED:
                # Possibly encountered a hidden or readonly file we can't
                # overwrite. Fall back on old code
                pass
            else:
                raise

    copy(src, dst, follow_symlinks=follow_symlinks)
    simplecopystat(src, dst, follow_symlinks=follow_symlinks)
    return dst
