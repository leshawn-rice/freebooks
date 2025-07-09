from setuptools import setup, find_packages
from pathlib import Path

# read the long description from README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="freebooks",
    version="0.1.0",
    author="Leshawn Rice",
    author_email="leshawn.rice@yahoo.com",
    description="Convert Audible AAX to common audio formats\n(requires ffmpeg, awk, grep installed in /usr/local/bin)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leshawn-rice/freebooks",
    packages=find_packages(),           # finds freebooks and its subpackages
    include_package_data=True,         # respects MANIFEST.in
    entry_points={
        "console_scripts": ["freebooks = freebooks.main:main"],
    },
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
)
