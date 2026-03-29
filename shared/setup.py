"""Setup for variance-shared installable package."""

from setuptools import find_packages, setup

setup(
    name="variance-shared",
    version="0.1.0",
    description="Shared library for FP&A Variance Analysis Agent",
    packages=find_packages(where=".."),
    package_dir={"": ".."},
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
        "pyyaml>=6.0",
        "pandas>=2.0",
        "numpy>=1.24",
        "pyarrow>=14.0",
    ],
)
