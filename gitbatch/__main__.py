#!/usr/bin/env python3
"""Main program."""

import argparse
import logging
import os
import sys
from urllib.parse import urlparse

import git

from gitbatch import __version__

logger = logging.getLogger("gitbatch")
formatter = logging.Formatter("[%(levelname)s] %(message)s")

cmdlog = logging.StreamHandler()
cmdlog.setLevel(logging.ERROR)
cmdlog.setFormatter(formatter)
logger.addHandler(cmdlog)


def sysexit(self, code=1):
    sys.exit(code)


def sysexit_with_message(msg, code=1):
    logger.error(str(msg))
    sysexit(code)


def normalize_path(path):
    if path:
        return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def repos_from_file(src):
    repos = []
    with open(src, "r") as f:
        for num, line in enumerate(f, start=1):
            repo = {}
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    url, branch, dest = [x.strip() for x in line.split(";")]
                except ValueError as e:
                    sysexit_with_message("Wrong numer of delimiters in line {line_num}: {exp}".format(
                        line_num=num, exp=e))

                if url:
                    url_parts = urlparse(url)

                    repo["url"] = url
                    repo["branch"] = branch or "master"
                    repo["name"] = os.path.basename(url_parts.path)
                    repo["dest"] = normalize_path(dest) or normalize_path("./{}".format(repo["name"]))

                    repos.append(repo)
                else:
                    sysexit_with_message("Repository Url is not set on line {line_num}".format(
                        line_num=num))
    return repos


def repos_clone(repos, ignore_existing):
    for repo in repos:
        print(repo)
        try:
            git.Repo.clone_from(repo["url"], repo["dest"], multi_options=["--branch=docs", "--single-branch"])
        except git.exc.GitCommandError as e:
            if not ignore_existing:
                err_raw = [x.strip() for x in e.stderr.split(":")][2]
                err = err_raw.splitlines()[0].split(".")[0]
                sysexit_with_message("Git error: {}".format(err))
            else:
                pass


def main():
    """Run main program."""
    parser = argparse.ArgumentParser(
        description=("Clone single branch from all repositories listed in a file"))
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))

    parser.parse_args()

    input_file_raw = os.environ.get("GIT_BATCH_INPUT_FILE", "./batchfile")
    input_file = normalize_path(input_file_raw)

    ignore_existing = os.environ.get("GIT_BATCH_IGNORE_EXISTING", True)

    if os.path.isfile(input_file):
        repos = repos_from_file(input_file)
        repos_clone(repos, ignore_existing)
    else:
        sysexit_with_message("The given batch file at '{}' does not exist".format(
            os.path.relpath(os.path.join("./", input_file))))


if __name__ == "__main__":
    main()
