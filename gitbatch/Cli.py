#!/usr/bin/env python3
"""Main program."""

import argparse
import logging
import os
import sys

from collections import defaultdict
from urllib.parse import urlparse

import git

from gitbatch import __version__
from gitbatch.Logging import SingleLog
from gitbatch.Utils import normalize_path, to_bool


class GitBatch:

    def __init__(self):
        self.log = SingleLog()
        self.logger = self.log.logger
        self.args = self._cli_args()
        self.config = self._config()
        self.run()

    def _cli_args(self):
        parser = argparse.ArgumentParser(
            description=("Clone single branch from all repositories listed in a file"))
        parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))

        return parser.parse_args()

    def _config(self):
        config = defaultdict(dict)
        input_file_raw = os.environ.get("GIT_BATCH_INPUT_FILE", "./batchfile")
        config["input_file"] = normalize_path(input_file_raw)

        config["ignore_existing"] = to_bool(os.environ.get("GIT_BATCH_IGNORE_EXISTING_REPO", True))
        config["ignore_missing"] = to_bool(os.environ.get("GIT_BATCH_IGNORE_MISSING_REMOTE", True))

        return config

    def _repos_from_file(self, src):
        repos = []
        with open(src, "r") as f:
            for num, line in enumerate(f, start=1):
                repo = {}
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        url, branch, dest = [x.strip() for x in line.split(";")]
                    except ValueError as e:
                        self.log.sysexit_with_message("Wrong numer of delimiters in line {line_num}: {exp}".format(
                            line_num=num, exp=e))

                    if url:
                        url_parts = urlparse(url)

                        repo["url"] = url
                        repo["branch"] = branch or "master"
                        repo["name"] = os.path.basename(url_parts.path)
                        repo["dest"] = normalize_path(dest) or normalize_path("./{}".format(repo["name"]))

                        repos.append(repo)
                    else:
                        self.log.sysexit_with_message("Repository Url is not set on line {line_num}".format(
                            line_num=num))
        return repos

    def _repos_clone(self, repos, ignore_existing):
        for repo in repos:
            try:
                options = [
                    "--branch={}".format(repo["branch"]),
                    "--single-branch"
                ]
                git.Repo.clone_from(repo["url"], repo["dest"], multi_options=options)
            except git.exc.GitCommandError as e:
                passed = False
                err_raw = e.stderr.strip().splitlines()[:-1]
                err = [x.split(":", 1)[1].strip() for x in err_raw]

                if any(["already exists and is not an empty directory" in item for item in err]):
                    if self.config["ignore_existing"]:
                        passed = True

                if any(["Could not find remote branch" in item for item in err]):
                    if self.config["ignore_missing"]:
                        passed = True

                if not passed:
                    self.log.sysexit_with_message("Git error: " + "\n".join(err))

    def run(self):
        if os.path.isfile(self.config["input_file"]):
            repos = self._repos_from_file(self.config["input_file"])
            self._repos_clone(repos, self.config["ignore_existing"])
        else:
            self.log.sysexit_with_message("The given batch file at '{}' does not exist".format(
                os.path.relpath(os.path.join("./", self.config["input_file"]))))
