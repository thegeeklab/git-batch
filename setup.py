#!/usr/bin/env python3
"""Setup script for the package."""

import io
import os
import re

from setuptools import find_packages
from setuptools import setup

PACKAGE_NAME = "gitbatch"


def get_property(prop, project):
    current_dir = os.path.dirname(os.path.realpath(__file__))
    result = re.search(
        r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop),
        open(os.path.join(current_dir, project, "__init__.py")).read())
    return result.group(1)


def get_readme(filename="README.md"):
    this = os.path.abspath(os.path.dirname(__file__))
    with io.open(os.path.join(this, filename), encoding="utf-8") as f:
        long_description = f.read()
    return long_description


setup(
    name=get_property("__project__", PACKAGE_NAME),
    version=get_property("__version__", PACKAGE_NAME),
    description="Clone single branch from all repositories listed in a file.",
    author=get_property("__author__", PACKAGE_NAME),
    author_email=get_property("__email__", PACKAGE_NAME),
    url=get_property("__url__", PACKAGE_NAME),
    license=get_property("__license__", PACKAGE_NAME),
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["*.tests", "tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Topic :: Software Development",
        "Topic :: Software Development :: Documentation",
    ],
    install_requires=[
        "gitpython",
        "colorama",
        "python-json-logger",
    ],
    entry_points={
        "console_scripts": [
            "git-batch = gitbatch.__main__:main"
        ]
    },
    test_suite="tests"
)
