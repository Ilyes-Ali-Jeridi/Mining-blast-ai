#!/usr/bin/env python3
"""
Setup script for Automated Drill-and-Blast System
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="automated-drill-blast-system",
    version="0.1.0",
    author="Mining Engineering Team",
    author_email="engineering@mining.com",
    description="Automated Drill-and-Blast System for Mining Operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mining/automated-drill-blast-system",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Manufacturing",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "ml": [
            "scikit-learn>=1.3.0",
            "xgboost>=1.7.0",
            "opencv-python>=4.8.0",
        ],
        "simulation": [
            "pygad>=3.0.0",
            "deap>=1.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "drill-blast-system=drill_blast_system.cli:main",
        ],
    },
)