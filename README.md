# FreeBooks

[![PyPI version](https://badge.fury.io/py/freebooks.svg)](https://pypi.org/project/freebooks/)

FreeBooks is a command-line tool for converting Audible AAX files into common audio formats (MP3, M4A, FLAC, WAV, Opus). It bundles all required tables and binaries (including `rcrack`) and exposes a simple `freebooks` CLI.

## Features

- Decrypt and convert AAX files using your activation bytes
- Supports multiple output formats: `mp3`, `m4a`, `flac`, `wav`, `opus`
- Automatically overwrites existing files with `-f`/`--force`
- Verbose logging mode for debugging
- Self-contained package including native tables & binaries

## Prerequisites

Before installing or running FreeBooks, ensure the following executables are **installed under** `/usr/bin` **and** are executable:

- `/usr/bin/ffmpeg`  
- `/usr/bin/awk`  
- `/usr/bin/grep`  

You can verify each is on your `$PATH` and executable:

```bash
ls -l /usr/bin/ffmpeg /usr/bin/awk /usr/bin/grep
```

## Installation

Install with pip:

```bash
pip install freebooks
```

Or, to build and install from source:

```bash
git clone https://github.com/leshawn-rice/freebooks.git
cd freebooks
python3 -m pip install --upgrade build
python3 -m build
pip install dist/freebooks-*.whl
```

## Usage

```bash
freebooks INPUT_FILE.aax [options]
```

### Arguments

- **INPUT_FILE**  
  Path to the `.aax` file you wish to convert.

### Options

- `-o`, `--output-file OUTPUT_FILE`  
  Destination path for the converted file. Default: `output.mp3`.
- `-t`, `--output-type FORMAT`  
  Output format: one of `mp3`, `m4a`, `flac`, `wav`, `opus`. Default: `mp3`.
- `-f`, `--force`  
  Overwrite existing output file without prompting.
- `-v`, `--verbose`  
  Enable verbose logging.

## Examples

Convert `book.aax` to `chapter1.mp3`:

```bash
freebooks book.aax -o chapter1.mp3
```

Convert with overwrite and verbose logging:

```bash
freebooks book.aax -o chapter1.m4a -t m4a -f -v
```

## Development

Clone the repo, install developer dependencies, and run tests:

```bash
git clone https://github.com/leshawn-rice/freebooks.git
cd freebooks
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade build
pip install -e .[dev]
```

## License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**.  
You may use, copy, modify, and distribute the code for **non-commercial** purposes only.  

Commercial use of the **bundled RainbowCrack** binary (in `freebooks/aax_tables/rcrack`) is **prohibited** unless you obtain a separate commercial license from the RainbowCrack authors.

For full license text, see [LICENSE](LICENSE).  
For RainbowCrack licensing details, see `freebooks/aax_tables/README.md`.