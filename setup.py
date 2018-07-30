import os

from setuptools import find_packages, setup

this_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(this_path)


setup(
    name="aio-fitbit",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'aioauth-client',
        'pyyaml',
        'frozendict',
        'frozenordereddict',
        'pandas',
        'numpy',
        'matplotlib',
        'tables',
    ],
    tests_require=[
        'fitbit',

        'coverage',
        'flake8',
        'flake8-import-order',
        'flake8_docstrings',
        'pep8-naming',
    ],

    include_package_data=True,
)
