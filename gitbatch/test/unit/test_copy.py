import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import pytest
from typing import List, Optional, Union, Any, Callable, Tuple
from pathlib import Path

from gitbatch.utils.copy import (
    _islink,
    _copytree,
    simple_copy_tree,
    simple_copy_stat,
    simple_copy,
)

@pytest.mark.parametrize(
    "path_type,is_link",
    [
        ("DirEntry", False),
        ("string", False),
        ("symlink", True),
    ],
)
def test_islink(path_type: str, is_link: bool) -> None:
    """Test the _islink function with different path types."""
    if path_type == "DirEntry":
        mock_entry = MagicMock()
        mock_entry.is_symlink.return_value = is_link
        assert _islink(mock_entry) is is_link
    elif path_type == "string":
        with tempfile.NamedTemporaryFile() as tmp:
            assert _islink(tmp.name) is False
    elif path_type == "symlink":
        with tempfile.NamedTemporaryFile() as tmp:
            link_path = tmp.name + "_link"
            os.symlink(tmp.name, link_path)
            assert _islink(link_path) is True
            os.unlink(link_path)

@pytest.mark.parametrize(
    "symlinks,ignore_dangling,dirs_exist_ok",
    [
        (False, False, True),
        (True, False, True),
        (False, True, True),
    ],
)
def test_copytree(tmp_path: Path, symlinks: bool, ignore_dangling: bool, dirs_exist_ok: bool) -> None:
    """Test the _copytree function with different parameters."""
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    # Create some files in source directory
    src_file = src_dir / "test.txt"
    src_file.write_text("test content")

    # Mock os.scandir to return our test file
    mock_entry = MagicMock()
    mock_entry.name = "test.txt"
    mock_entry.is_symlink.return_value = False
    mock_entry.is_dir.return_value = False

    with patch("os.scandir", return_value=[mock_entry]):
        result = _copytree(
            entries=[mock_entry],
            src=str(src_dir),
            dst=str(dst_dir),
            symlinks=symlinks,
            ignore=None,
            ignore_dangling_symlinks=ignore_dangling,
            dirs_exist_ok=dirs_exist_ok,
        )

    assert result == str(dst_dir)
    assert (dst_dir / "test.txt").exists()

@pytest.mark.parametrize(
    "symlinks,ignore_dangling,dirs_exist_ok",
    [
        (False, False, True),
        (True, False, True),
        (False, True, True),
    ],
)
def test_simple_copy_tree(tmp_path: Path, symlinks: bool, ignore_dangling: bool, dirs_exist_ok: bool) -> None:
    """Test the simple_copy_tree function with different parameters."""
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    # Create some files in source directory
    src_file = src_dir / "test.txt"
    src_file.write_text("test content")

    result = simple_copy_tree(
        str(src_dir),
        str(dst_dir),
        symlinks=symlinks,
        ignore=None,
        ignore_dangling_symlinks=ignore_dangling,
        dirs_exist_ok=dirs_exist_ok,
    )

    assert result == str(dst_dir)
    assert (dst_dir / "test.txt").exists()

def test_simple_copy_stat(tmp_path: Path) -> None:
    """Test the simple_copy_stat function."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.write_text("test")
    dst.write_text("test")

    # Just test that it doesn't raise an exception
    simple_copy_stat(str(src), str(dst))

@pytest.mark.parametrize(
    "follow_symlinks",
    [True, False],
)
def test_simple_copy(tmp_path: Path, follow_symlinks: bool) -> None:
    """Test the simple_copy function with different follow_symlinks values."""
    src = tmp_path / "src"
    src.write_text("test content")
    dst = tmp_path / "copy.txt"

    result = simple_copy(str(src), str(dst), follow_symlinks=follow_symlinks)

    assert result == str(dst)
    assert dst.exists()
    assert dst.exists()
