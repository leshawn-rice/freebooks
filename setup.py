from setuptools import setup, find_packages
from pathlib import Path

# read the long description from README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="freebooks",
    version="0.1.4",
    author="Leshawn Rice",
    author_email="leshawn.rice@yahoo.com",
    description=(
        "Convert Audible AAX to common audio formats "
        "(requires ffmpeg, awk, grep installed in /usr/bin)."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leshawn-rice/freebooks",
    license="PolyForm Noncommercial License 1.0.0",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": ["freebooks = freebooks.main:main"],
    },
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
)
