#!/usr/bin/env python3
"""Main program."""

import argparse
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from shutil import ignore_patterns
from urllib.parse import urlparse

import git

from gitbatch import __version__
from gitbatch.logging import SingleLog
from gitbatch.utils import copy, normalize_path, to_bool


class GitBatch:
    """Handles git operations."""

    def __init__(self):
        self.log = SingleLog()
        self.logger = self.log.logger
        self.args = self._cli_args()
        self.config = self._config()
        self.run()

    def _cli_args(self):
        parser = argparse.ArgumentParser(
            description=("Clone single branch from all repositories listed in a file")
        )
        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
        parser.add_argument(
            "-v", dest="logging.level", action="append_const", const=-1, help="increase log level"
        )
        parser.add_argument(
            "-q", dest="logging.level", action="append_const", const=1, help="decrease log level"
        )

        return parser.parse_args()

    def _config(self):
        config = defaultdict(dict)

        # Override correct log level from argparse
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_level = levels.index("ERROR")
        tmp_dict = self.args.__dict__
        if tmp_dict.get("logging.level"):
            for adjustment in tmp_dict["logging.level"]:
                log_level = min(len(levels) - 1, max(log_level + adjustment, 0))
        config["logging"]["level"] = levels[log_level]

        input_file_raw = os.environ.get("GIT_BATCH_INPUT_FILE", ".batchfile")
        config["input_file"] = normalize_path(input_file_raw)

        config["ignore_existing"] = to_bool(os.environ.get("GIT_BATCH_IGNORE_EXISTING", True))
        config["ignore_missing"] = to_bool(os.environ.get("GIT_BATCH_IGNORE_MISSING_REMOTE", True))

        return config

    def _repos_from_file(self, src):
        repos = []
        with open(src) as f:
            for num, line in enumerate(f, start=1):
                repo = {}
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        url, src, dest = (x.strip() for x in line.split(";"))
                        branch, *_ = (x.strip() for x in src.split(":"))

                        path = None
                        if len(_) > 0:
                            path = Path(_[0])
                            path = path.relative_to(path.anchor)

                    except ValueError as e:
                        self.log.sysexit_with_message(
                            f"Wrong numer of delimiters in line {num}: {e}"
                        )

                    if url:
                        url_parts = urlparse(url)

                        repo["url"] = url
                        repo["branch"] = branch or "main"
                        repo["path"] = path
                        repo["name"] = os.path.basename(url_parts.path)
                        repo["rel_dest"] = dest
                        repo["dest"] = normalize_path(dest) or normalize_path(
                            "./{}".format(repo["name"])
                        )

                        repos.append(repo)
                    else:
                        self.log.sysexit_with_message(f"Repository Url is not set on line {num}")
        return repos

    def _repos_clone(self, repos):
        for repo in repos:
            with tempfile.TemporaryDirectory(prefix="gitbatch_") as tmp:
                try:
                    options = ["--branch={}".format(repo["branch"]), "--single-branch"]
                    git.Repo.clone_from(repo["url"], tmp, multi_options=options)
                    os.makedirs(repo["dest"], 0o750, self.config["ignore_existing"])
                except git.exc.GitCommandError as e:
                    skip = False
                    err_raw = e.stderr.strip().splitlines()[:-1]
                    err = [
                        x.split(":", 1)[1].strip().replace(repo["dest"], repo["rel_dest"])
                        for x in err_raw
                    ]

                    if (
                        any("could not find remote branch" in item for item in err)
                        and self.config["ignore_missing"]
                    ):
                        skip = True
                    if not skip:
                        self.log.sysexit_with_message("Error: {}".format("\n".join(err)))
                except FileExistsError:
                    self._file_exist_handler()

                try:
                    path = tmp
                    if repo["path"]:
                        path = normalize_path(os.path.join(tmp, repo["path"]))
                        if not os.path.isdir(path):
                            raise FileNotFoundError(Path(path).relative_to(tmp))

                    copy.simplecopytree(
                        path,
                        repo["dest"],
                        ignore=ignore_patterns(".git"),
                        dirs_exist_ok=self.config["ignore_existing"],
                    )
                except FileExistsError:
                    self._file_exist_handler()
                except FileNotFoundError as e:
                    self.log.sysexit_with_message(
                        "Error: directory '{}' not found in repository '{}'".format(
                            e, repo["name"]
                        )
                    )

    def _file_exist_handler(self):
        skip = False
        err = ["direcory already exists"]

        if self.config["ignore_existing"]:
            self.logger.warning("Error: {}".format("\n".join(err)))
            skip = True
        if not skip:
            self.log.sysexit_with_message("Error: {}".format("\n".join(err)))

    def run(self):
        self.log.set_level(self.config["logging"]["level"])
        if os.path.isfile(self.config["input_file"]):
            repos = self._repos_from_file(self.config["input_file"])
            self._repos_clone(repos)
        else:
            self.log.sysexit_with_message(
                "The given batch file at '{}' does not exist".format(
                    os.path.relpath(os.path.join("./", self.config["input_file"]))
                )
            )


def main():
    GitBatch()
