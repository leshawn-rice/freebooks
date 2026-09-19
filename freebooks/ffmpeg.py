"""Locate an ffmpeg binary without requiring a system-wide installation.

A system ffmpeg is preferred when one is installed, because distributions keep
it patched. The build shipped in the ``imageio-ffmpeg`` wheel is the fallback,
so a plain ``pip install freebooks`` still works on a machine with no ffmpeg at
all. ``FREEBOOKS_FFMPEG`` overrides both.
"""

import os
import shutil

FFMPEG_ENV_VAR = "FREEBOOKS_FFMPEG"


def _is_executable(path):
    """
    Check that a path points at a file we are allowed to execute.

    :param path: Optional[str]
        Candidate path to an executable.
    :returns: bool
        True if the path is an executable file.
    """
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _bundled_ffmpeg():
    """
    Return the ffmpeg binary shipped with imageio-ffmpeg, if installed.

    :returns: Optional[str]
        Path to the bundled ffmpeg binary, or None if it cannot be used.
    """
    try:
        import imageio_ffmpeg
    except ImportError:
        return None

    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

    return exe if _is_executable(exe) else None


def find_ffmpeg():
    """
    Resolve the ffmpeg binary to use for conversions.

    Resolution order: the ``FREEBOOKS_FFMPEG`` environment variable, any ffmpeg
    found on ``PATH``, then the binary bundled with imageio-ffmpeg. A system
    ffmpeg wins because it receives security updates from its distribution,
    while the bundled build is pinned to whatever imageio-ffmpeg last shipped.

    :returns: Optional[str]
        Path to an ffmpeg binary, or None if none is available.
    """
    override = os.environ.get(FFMPEG_ENV_VAR)
    if _is_executable(override):
        return override

    from_path = shutil.which("ffmpeg")
    if _is_executable(from_path):
        return from_path

    return _bundled_ffmpeg()


def get_ffmpeg():
    """
    Resolve the ffmpeg binary, raising if none can be found.

    :returns: str
        Path to an ffmpeg binary.
    :raises RuntimeError:
        If no usable ffmpeg binary is available.
    """
    exe = find_ffmpeg()
    if not exe:
        raise RuntimeError(
            "No ffmpeg binary available. Install ffmpeg on your PATH, reinstall "
            "freebooks (which bundles one via imageio-ffmpeg), or point "
            f"{FFMPEG_ENV_VAR} at an ffmpeg binary."
        )
    return exe
