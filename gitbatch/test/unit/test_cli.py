import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from gitbatch.cli import GitBatch

@pytest.fixture
def gitbatch_instance() -> GitBatch:
    """Create a GitBatch instance with run() method mocked to prevent execution."""
    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args, \
         patch.object(GitBatch, "run") as mock_run:
        mock_parse_args.return_value = MagicMock()
        mock_run.return_value = None
        return GitBatch()

def test_initialization(gitbatch_instance: GitBatch) -> None:
    """Test that GitBatch initializes correctly."""
    assert gitbatch_instance.log is not None
    assert gitbatch_instance.logger is not None
    assert gitbatch_instance.args is not None
    assert gitbatch_instance.config is not None

def test_cli_args(gitbatch_instance: GitBatch) -> None:
    """Test that CLI arguments are parsed correctly."""
    # Test that args is a namespace object
    assert hasattr(gitbatch_instance.args, "__dict__")

def test_config(gitbatch_instance: GitBatch) -> None:
    """Test that configuration is set up correctly."""
    with patch("os.environ.get") as mock_get:
        mock_get.side_effect = lambda key, default=None: {
            "GIT_BATCH_INPUT_FILE": ".test_batchfile",
            "GIT_BATCH_IGNORE_EXISTING": "true",
            "GIT_BATCH_IGNORE_MISSING_REMOTE": "false",
        }.get(key, default)

        # Recreate the config
        config = gitbatch_instance._config()

        # Check the values without comparing the full path
        assert config["input_file"].endswith(".test_batchfile")
        assert config["ignore_existing"] is True
        assert config["ignore_missing"] is False

def test_repos_from_file(tmp_path: Path, gitbatch_instance: GitBatch) -> None:
    """Test that repositories are correctly parsed from a file."""
    # Create a test file
    test_file = tmp_path / "test_repos.txt"
    test_file.write_text("https://github.com/example/repo.git;main:subdir;./dest\n")

    # Test with valid file
    repos = gitbatch_instance._repos_from_file(str(test_file))
    assert len(repos) == 1
    assert repos[0]["url"] == "https://github.com/example/repo.git"
    assert repos[0]["branch"] == "main"
    assert repos[0]["path"] == Path("subdir")
    assert repos[0]["rel_dest"] == "./dest"
    # Just check that dest ends with the expected path
    assert repos[0]["dest"].endswith("dest")
    assert repos[0]["name"] == "repo.git"

def test_repos_from_file_empty(tmp_path: Path, gitbatch_instance: GitBatch) -> None:
    """Test that empty lines are skipped."""
    # Create an empty file
    test_file = tmp_path / "empty.txt"
    test_file.write_text("\n")

    repos = gitbatch_instance._repos_from_file(str(test_file))
    assert len(repos) == 0

def test_repos_from_file_comment(tmp_path: Path, gitbatch_instance: GitBatch) -> None:
    """Test that comment lines are skipped."""
    # Create a file with a comment
    test_file = tmp_path / "comment.txt"
    test_file.write_text("# This is a comment\n")

    repos = gitbatch_instance._repos_from_file(str(test_file))
    assert len(repos) == 0

def test_repos_from_file_invalid_format(tmp_path: Path, gitbatch_instance: GitBatch) -> None:
    """Test that invalid format raises an error."""
    # Create a file with invalid format
    test_file = tmp_path / "invalid.txt"
    test_file.write_text("invalid;format\n")

    with pytest.raises(SystemExit):
        gitbatch_instance._repos_from_file(str(test_file))

def test_file_exist_handler(gitbatch_instance: GitBatch) -> None:
    """Test that file existence is handled correctly."""
    # Test with ignore_existing=True
    gitbatch_instance.config["ignore_existing"] = True
    with patch.object(gitbatch_instance.logger, "warning") as mock_warning:
        gitbatch_instance._file_exist_handler()
        mock_warning.assert_called_once_with("Error: directory already exists")

    # Test with ignore_existing=False
    gitbatch_instance.config["ignore_existing"] = False
    with patch.object(gitbatch_instance.log, "sysexit") as mock_log:
        gitbatch_instance._file_exist_handler()
        mock_log.assert_called_once()

def test_run(gitbatch_instance: GitBatch) -> None:
    """Test that run method executes correctly."""
    with patch("os.path.isfile") as mock_isfile:
        mock_isfile.return_value = True

        with patch.object(GitBatch, "_repos_from_file") as mock_repos_from_file, \
             patch.object(GitBatch, "_repos_clone") as mock_repos_clone:

            mock_repos_from_file.return_value = []
            gitbatch_instance.run()

            mock_isfile.assert_called_once()
            mock_repos_from_file.assert_called_once()
            mock_repos_clone.assert_called_once()

        # Test with non-existent file
        mock_isfile.reset_mock()
        mock_isfile.return_value = False

        with patch.object(gitbatch_instance.log, "sysexit") as mock_log:
            gitbatch_instance.run()
            mock_log.assert_called_once()
