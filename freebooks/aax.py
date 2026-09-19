"""Pure-Python reader for the AAX metadata FreeBooks needs.

The activation code lookup needs the file checksum that ffmpeg prints as
``[aax] file checksum == ...``. That value lives in the ``adrm`` atom, so we read
it directly instead of shelling out to ffprobe and parsing its logs.
"""

import os
import struct

# Layout of the adrm atom payload, per ffmpeg's mov_read_adrm(): 8 bytes, then a
# 56-byte drm blob, then 4 bytes, then the 20-byte file checksum.
CHECKSUM_OFFSET = 8 + 56 + 4
CHECKSUM_SIZE = 20
MIN_ADRM_SIZE = 8 + CHECKSUM_OFFSET + CHECKSUM_SIZE
MAX_ADRM_SIZE = 1 << 20

_SCAN_CHUNK_SIZE = 1 << 20


def _iter_top_level_atoms(handle, file_size):
    """
    Yield the top-level atoms of an MP4/AAX container.

    :param handle: BinaryIO
        Seekable handle opened on the container.
    :param file_size: int
        Total size of the container in bytes.
    :yields: tuple[bytes, int, int, int]
        The atom type, its offset, its total size, and its header length.
    """
    offset = 0
    while offset < file_size - 8:
        handle.seek(offset)
        header = handle.read(8)
        if len(header) < 8:
            return

        size, atom_type = struct.unpack(">I4s", header)
        header_size = 8

        if size == 1:  # 64-bit size follows the type
            raw_size = handle.read(8)
            if len(raw_size) < 8:
                return
            size = struct.unpack(">Q", raw_size)[0]
            header_size = 16
        elif size == 0:  # atom extends to end of file
            size = file_size - offset

        if size < header_size:
            return

        yield atom_type, offset, size, header_size
        offset += size


def _find_adrm_atom(handle, start, length):
    """
    Scan a region of the container for the ``adrm`` atom.

    The atom is nested inside the ``aavd`` sample entry rather than a standard
    container atom, so we scan for its signature and validate the size field
    that precedes it instead of walking sample-entry internals.

    :param handle: BinaryIO
        Seekable handle opened on the container.
    :param start: int
        Byte offset to start scanning from.
    :param length: int
        Number of bytes to scan.
    :returns: Optional[int]
        Offset of the start of the adrm atom, or None if it is not present.
    """
    position = start
    remaining = length
    carry = b""

    while remaining > 0:
        handle.seek(position)
        buffer = handle.read(min(_SCAN_CHUNK_SIZE, remaining))
        if not buffer:
            return None

        window = carry + buffer
        window_start = position - len(carry)

        index = -1
        while True:
            index = window.find(b"adrm", index + 1)
            if index < 0:
                break
            if index < 4:
                continue
            size = struct.unpack(">I", window[index - 4:index])[0]
            if MIN_ADRM_SIZE <= size <= MAX_ADRM_SIZE:
                return window_start + index - 4

        carry = window[-8:]
        position += len(buffer)
        remaining -= len(buffer)

    return None


def read_file_checksum(path):
    """
    Read the AAX file checksum from the container's adrm atom.

    :param path: str
        Path to the AAX file.
    :returns: Optional[str]
        The checksum as a lowercase hex string, or None if the file carries no
        readable adrm atom (for example, a non-AAX input).
    """
    file_size = os.path.getsize(path)

    with open(path, "rb") as handle:
        for atom_type, offset, size, header_size in _iter_top_level_atoms(handle, file_size):
            if atom_type != b"moov":
                continue

            adrm_offset = _find_adrm_atom(
                handle, offset + header_size, size - header_size)
            if adrm_offset is None:
                continue

            handle.seek(adrm_offset + 8 + CHECKSUM_OFFSET)
            checksum = handle.read(CHECKSUM_SIZE)
            if len(checksum) == CHECKSUM_SIZE:
                return checksum.hex()

    return None
