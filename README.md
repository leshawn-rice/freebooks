# FreeBooks

[![PyPI version](https://badge.fury.io/py/freebooks.svg)](https://pypi.org/project/freebooks/) [![Tests](https://github.com/leshawn-rice/freebooks/actions/workflows/tests.yml/badge.svg)](https://github.com/leshawn-rice/freebooks/actions/workflows/tests.yml)

**Source code:** [github.com/leshawn-rice/freebooks](https://github.com/leshawn-rice/freebooks) — issues and pull requests welcome.

FreeBooks is a command-line tool for converting Audible AAX files into common audio formats (MP3, M4A, FLAC, WAV, Opus). It bundles all required tables and binaries (including `rcrack`) and exposes a simple `freebooks` CLI.

## Features

- Decrypt and convert AAX files using your activation bytes
- Supports multiple output formats: `mp3`, `m4a`, `flac`, `wav`, `opus`
- Automatically overwrites existing files with `-f`/`--force`
- Verbose logging mode for debugging
- Self-contained package including ffmpeg, native tables & binaries — no external tools to install

## Prerequisites

None beyond Python 3.7+ on 64-bit Linux. FreeBooks is self-contained:

- **ffmpeg** is installed automatically as a dependency ([`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/) ships a static build), so you do not need ffmpeg on your system. If you already have one installed, FreeBooks uses yours.
- **`awk` and `grep` are no longer used at all** — metadata parsing is done in pure Python.
- `rcrack` and its rainbow tables are bundled in the package.

If you would rather use your own ffmpeg build, point FreeBooks at it:

```bash
export FREEBOOKS_FFMPEG=/usr/bin/ffmpeg
```

FreeBooks looks for ffmpeg in this order: `$FREEBOOKS_FFMPEG`, any `ffmpeg` on your `$PATH`, then the bundled build. A system ffmpeg wins because your distribution keeps it patched; the bundled build is there so the tool still works when you have none.

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

Clone the repo and install in editable mode:

```bash
git clone https://github.com/leshawn-rice/freebooks.git
cd freebooks
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Running tests

The suite uses only the standard library, so no extra test dependencies are needed:

```bash
python3 -m unittest discover -s tests -v
```

Tests run against **whichever ffmpeg FreeBooks resolves** — your system ffmpeg if you have one, otherwise the bundled build.
Anything that needs a binary FreeBooks cannot find is skipped rather than failed, so the
suite passes with or without ffmpeg installed.

To also run the end-to-end tests (checksum → activation code → conversion) against a real
book, point `FREEBOOKS_TEST_AAX` at an `.aax` file:

```bash
FREEBOOKS_TEST_AAX=~/books/book.aax python3 -m unittest discover -s tests -v
```

If the file does not exist, those tests are skipped with a warning rather than failing.

To check the suite against a specific ffmpeg build:

```bash
FREEBOOKS_FFMPEG=/usr/bin/ffmpeg python3 -m unittest discover -s tests -v
```

Every push and pull request runs the same suite on GitHub Actions across Python 3.8, 3.10 and
3.12, plus two extra jobs that run it with the bundled ffmpeg only and with no ffmpeg at all.

What the suite covers:

| Module | Covers |
| --- | --- |
| `tests/test_aax.py` | adrm atom parsing, 64-bit atoms, chunk boundaries, rcrack output parsing |
| `tests/test_cli.py` | argument parsing, path validation, dependency checks, overwrite rules, the `freebooks` entry point |
| `tests/test_conversion.py` | ffmpeg resolution order, per-format encoder flags, real conversions to all five formats |

## License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**.  
You may use, copy, modify, and distribute the code for **non-commercial** purposes only.  

Commercial use of the **bundled RainbowCrack** binary (in `freebooks/aax_tables/rcrack`) is **prohibited** unless you obtain a separate commercial license from the RainbowCrack authors.

For full license text, see [LICENSE](LICENSE).  
For RainbowCrack licensing details, see `freebooks/aax_tables/README.md`.