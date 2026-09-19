from setuptools import setup, find_packages
from pathlib import Path

# read the long description from README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="freebooks",
    version="1.1.0",
    author="Leshawn Rice",
    author_email="leshawn.rice@yahoo.com",
    description=(
        "Convert Audible AAX to common audio formats "
        "(ffmpeg included, no external tools required)."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leshawn-rice/freebooks",
    project_urls={
        "Source": "https://github.com/leshawn-rice/freebooks",
        "Issue Tracker": "https://github.com/leshawn-rice/freebooks/issues",
    },
    license="PolyForm Noncommercial License 1.0.0",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": ["freebooks = freebooks.main:main"],
    },
    install_requires=["imageio-ffmpeg>=0.4.9"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
)
