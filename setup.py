#!/usr/bin/env python3

import os
from setuptools import setup

from phockup.__main__ import __version__


_CUR_DIR = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(_CUR_DIR, "README.md"), "r", encoding="utf-8") as f:
    readme = f.read()

setup(
    name="phockup",
    version=__version__,
    description="Media sorting tool to organize photos and videos from your camera in folders by year, month and day. The software will collect all files from the input directory and copy them to the output directory without changing the files content. It will only rename the files and place them in the proper directory for year, month and day.",
    long_description=readme,
    author="Ivan Dokov",
    author_email="",
    url="https://github.com/ivandokov/phockup",
    license="MIT",
    keywords=[],
    packages=[
        "phockup",
    ],
    entry_points={
        "console_scripts": [
            "phockup = phockup.__main__:main",
        ]
    },
    options={
        "build_scripts": {},
    },
    classifiers=[
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        "python-dateutil",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-mock",
            "coverage",
        ],
    }
)
