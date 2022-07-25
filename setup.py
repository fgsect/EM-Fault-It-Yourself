#!/usr/bin/env python3

from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

setup(
    long_description=long_description,
    long_description_content_type='text/markdown',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    package_data={'emfi_station': ['web/*']},
)
