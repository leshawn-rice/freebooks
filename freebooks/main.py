import os
import sys
import argparse
import subprocess as sp
from freebooks.logger import ConsoleLogger
from pathlib import Path

_package_directory = Path(__file__).parent
rcrack = f"{_package_directory}/aax_tables/rcrack"

log = ConsoleLogger()


def check_external_tools():
    """Ensure required binaries exist in /usr/local/bin and are executable."""
    missing = []
    for exe in ("ffmpeg", "awk", "grep", "ffprobe"):
        path = Path("/usr/bin") / exe
        if not (path.is_file() and os.access(path, os.X_OK)):
            missing.append(str(path))
    if missing:
        log.error(
            "Missing required external tools:\n  %s\n"
            "Please install them and ensure they are executable.",
            "\n  ".join(missing),
        )
        sys.exit(1)


def parse_cli_arguments():
    """
    Parse command-line arguments for the openbook tool.

    :returns: argparse.Namespace
        Parsed arguments with the following attributes:
        - filename (str): Path to the input AAX file to be converted.
        - output_file (str): Destination path for the converted file.
        - output_type (str): Audio format for the output file (e.g., 'mp3', 'm4a').
        - force (bool): Overwrite existing output file without prompting.
        - verbose (bool): Enable verbose logging for debugging.
    """
    parser = argparse.ArgumentParser(
        prog="openbook",
        description="Convert AAX audio files to the specified format.",
    )
    parser.add_argument(
        "filename",
        metavar="INPUT_FILE",
        help="Path to the input AAX file to be converted",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        metavar="OUTPUT_FILE",
        default="output.mp3",
        help="Destination path for the converted file (default: %(default)s)",
    )
    parser.add_argument(
        "-t",
        "--output-type",
        metavar="FORMAT",
        default="mp3",
        choices=["mp3", "m4a", "flac", "wav", "opus"],
        help="Audio format for the output file (default: %(default)s)",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing output file without prompting",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging for debugging",
    )
    return parser.parse_args()


def get_input_path(filename):
    """
    Resolve and validate the input file path.

    :param filename: str
        A relative or absolute path to the file you want to process.
    :returns: str
        The absolute, validated path to the input file.
    :raises ValueError:
        If no file exists at the resolved path.
    """
    log.debug(f"Resolving absolute path for input file: {filename}")
    path = os.path.abspath(filename)
    log.debug("Resolved path: %s", path)

    if not os.path.exists(path):
        log.error(f"File not found at path: {path}")
        raise ValueError(f"Invalid file path: {path}")

    log.info(f"Input file found and validated: {path}")
    return path


def get_file_checksum(path):
    """
    Extract the checksum tag from an audio file using ffprobe, grep, and awk.

    :param path: str
        The absolute or relative path to the input audio file.
    :returns: str
        The checksum value parsed from the files metadata.
    :raises: RuntimeError
        If the checksum cannot be retrieved or an error occurs during execution.
    """
    log.debug(f"Starting checksum extraction for file: {path}")

    ffprobe_cmd = ["/usr/bin/ffprobe", path]
    grep_cmd = ["/usr/bin/grep",    "checksum"]
    awk_cmd = ["/usr/bin/awk",     "-F==", "{print $2}"]

    try:
        log.debug(f"Running ffprobe: {' '.join(ffprobe_cmd)}")
        ffprobe = sp.Popen(ffprobe_cmd, stdout=sp.PIPE, stderr=sp.STDOUT)

        log.debug(f"Piping ffprobe output to grep: {' '.join(grep_cmd)}")
        grep = sp.Popen(grep_cmd, stdin=ffprobe.stdout, stdout=sp.PIPE)
        ffprobe.stdout.close()

        log.debug(f"Piping grep output to awk: {' '.join(awk_cmd)}")
        checksum_bytes = sp.check_output(awk_cmd, stdin=grep.stdout)
        grep.stdout.close()

    except sp.CalledProcessError as cpe:
        log.error(f"Subprocess failed (return code {cpe.returncode}): {cpe}")
        raise RuntimeError(f"Failed to extract checksum for {path}") from cpe
    except Exception as exc:
        log.error(f"Unexpected error during checksum extraction: {exc}")
        raise RuntimeError(f"Error extracting checksum for {path}") from exc

    checksum = checksum_bytes.decode().strip()
    log.info(f"Checksum for {path}: {checksum}")
    return checksum


def get_activation_code(path, checksum):
    """
    Run the rcrack binary to generate an activation code for a given file.

    :param path: str
        Absolute or relative path to the input audio file.
    :param checksum: str
        The checksum string previously extracted from the file.
    :returns: str
        The activation code extracted from rcrack’s output.
    :raises: RuntimeError
        If rcrack invocation or parsing fails.
    """
    log.debug(f"Preparing to generate activation code for file: {path}")
    rcrack_dir = os.path.dirname(os.path.abspath(rcrack))

    rcrack_cmd = [rcrack, rcrack_dir, "-h", checksum]
    grep_cmd = ["/usr/bin/grep", "hex"]
    awk_cmd = ["/usr/bin/awk", "-Fhex:", "{print $2}"]

    log.debug(f"rcrack binary directory: {rcrack_dir}")
    log.debug(f"rcrack command: {' '.join(rcrack_cmd)}")

    current_dir = os.getcwd()
    try:
        os.chdir(rcrack_dir)
        log.debug(f"Changed working directory to rcrack_dir: {rcrack_dir}")

        log.debug("Running rcrack")
        proc_rcrack = sp.Popen(rcrack_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        proc_grep = sp.Popen(
            grep_cmd, stdin=proc_rcrack.stdout, stdout=sp.PIPE)
        proc_rcrack.stdout.close()

        log.debug(f"Filtering rcrack output with grep: {' '.join(grep_cmd)}")
        activation_bytes = sp.check_output(awk_cmd, stdin=proc_grep.stdout)
        proc_grep.stdout.close()

    except sp.CalledProcessError as cpe:
        log.error(f"Subprocess error (code {cpe.returncode}): {cpe}")
        raise RuntimeError(
            f"Failed to parse activation code for {path}") from cpe
    except Exception as exc:
        log.error(f"Unexpected error generating activation code: {exc}")
        raise RuntimeError(
            f"Error generating activation code for {path}") from exc
    finally:
        os.chdir(current_dir)
        log.debug(f"Restored working directory to: {current_dir}")

    activation_code = activation_bytes.decode().strip()
    log.info(f"Generated activation code for {path}: {activation_code}")
    return activation_code


def convert_file(input_path, output_path, activation_code, file_type=None):
    """
    Convert an audio file (e.g., AAX) to the specified format using ffmpeg.

    :param input_path: str
        Path to the input file to convert.
    :param output_path: str
        Path where the converted file will be written.
    :param activation_code: str
        Activation bytes used to decrypt the input file.
    :param file_type: Optional[str]
        Desired output format (e.g., 'mp3', 'm4a', 'flac'); if None, inferred from output_path extension.
    :returns: None
    :raises RuntimeError:
        If the ffmpeg conversion process fails.
    """
    log.debug(
        f"Starting conversion: input={input_path}, output={output_path}, file_type={file_type}")

    # determine output extension
    ext = (file_type or os.path.splitext(output_path)[1].lstrip('.')).lower()
    log.debug(f"Resolved output extension: {ext}")

    # map formats to ffmpeg audio codecs
    codec_map = {
        'mp3':  'libmp3lame',
        'm4a':  'aac',
        'aac':  'aac',
        'opus': 'libopus',
        'flac': 'flac',
        'wav':  'pcm_s16le',
    }

    # build ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # overwrite without asking
        "-activation_bytes", activation_code,
        "-i", input_path,
        "-vn",  # disable video streams
    ]

    if ext in codec_map:
        codec = codec_map[ext]
        log.debug(f"Using codec '{codec}' for format '{ext}'")
        ffmpeg_cmd += ["-c:a", codec, "-q:a", "2"]
    else:
        log.warning(f"No codec mapping for '{ext}'; using ffmpeg defaults")

    ffmpeg_cmd.append(output_path)
    log.debug(f"Executing ffmpeg command: {' '.join(ffmpeg_cmd)}")

    try:
        # suppress console output
        sp.run(ffmpeg_cmd, check=True, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    except sp.CalledProcessError as cpe:
        log.error(
            f"ffmpeg failed (exit code {cpe.returncode}) converting {input_path} to {output_path}")
        raise RuntimeError(f"Conversion failed for {input_path}") from cpe

    log.info(
        f"Successfully converted '{input_path}' to '{output_path}'")


def process_conversion(args: argparse.Namespace):
    check_external_tools()

    global log
    log = ConsoleLogger(verbose=args.verbose)

    input_path = get_input_path(args.filename)
    output_path = os.path.abspath(args.output_file)

    if os.path.exists(output_path) and not args.force:
        raise ValueError(
            "Output Path already exists! Use -f/--force to overwrite!")

    checksum = get_file_checksum(input_path)
    activation_code = get_activation_code(input_path, checksum)

    convert_file(input_path, output_path, activation_code, args.output_type)


def convert_aax_to_audio(input_file: str = None, output_file: str = "output.mp3", output_type: str = "mp3", force: bool = False, verbose: bool = False):
    args = argparse.Namespace(
        filename=input_file,
        output_file=output_file,
        output_type=output_type,
        force=force,
        verbose=verbose,
    )
    process_conversion(args)


def main():
    args = parse_cli_arguments()
    process_conversion(args)


if __name__ == "__main__":
    main()
