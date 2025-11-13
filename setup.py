from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vrp-solver",
    version="1.0.0",
    author="TMS Team",
    description="Advanced Vehicle Routing Problem Solver with Multi-Day Consolidation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Mathematics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "ortools>=9.7.0",
        "python-dateutil>=2.8.2",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": ["pytest>=7.3.0", "pytest-cov>=4.1.0", "black>=23.3.0", "flake8>=6.0.0"],
        "viz": ["matplotlib>=3.7.0", "plotly>=5.14.0"],
    },
)
