#!/usr/bin/env python

from setuptools import setup

setup(
    name="retrolauncher2",
    version="0.5.0",
    description="RetroLauncher 2",
    author="valadaa48",
    author_email="valadaa48@gmx.com",
    url="https://github.com/valadaa48/retrolauncher2",
    install_requires=["urwid", "toml", "evdev", "cachetools", "humanize"],
    include_package_data=True,
    packages=["retrolauncher", "retrolauncher.config", "retrolauncher.themes"],
    zip_safe=False,
    entry_points={
        "console_scripts": ["retrolauncher2 = retrolauncher.retrolauncher:main"]
    },
)
