"""Tests for the pure-Python replacements of the old ffprobe/grep/awk pipelines."""

import os
import struct
import tempfile
import unittest

from freebooks.aax import CHECKSUM_OFFSET, CHECKSUM_SIZE, read_file_checksum
from freebooks.main import parse_activation_code


def build_atom(atom_type, payload):
    """Build a plain MP4 atom with a 32-bit size header."""
    return struct.pack(">I4s", len(payload) + 8, atom_type) + payload


def build_adrm(checksum):
    """Build an adrm atom laid out the way ffmpeg's mov_read_adrm reads it."""
    payload = b"\x00" * CHECKSUM_OFFSET + checksum + b"\x00" * 4
    return build_atom(b"adrm", payload)


def build_aax(checksum, extra_moov=b""):
    """Build a minimal AAX-like container with adrm nested in a sample entry."""
    sample_entry = build_atom(b"aavd", b"\x00" * 28 + build_adrm(checksum))
    stsd = build_atom(b"stsd", b"\x00" * 8 + sample_entry)
    stbl = build_atom(b"stbl", stsd)
    minf = build_atom(b"minf", stbl)
    mdia = build_atom(b"mdia", minf)
    trak = build_atom(b"trak", mdia)
    moov = build_atom(b"moov", extra_moov + trak)
    return build_atom(b"ftyp", b"aax \x00\x00\x00\x00") + moov + build_atom(b"mdat", b"\x11" * 64)


class ReadFileChecksumTests(unittest.TestCase):
    def write_file(self, data):
        handle = tempfile.NamedTemporaryFile(suffix=".aax", delete=False)
        handle.write(data)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_reads_checksum_from_nested_adrm(self):
        checksum = bytes(range(CHECKSUM_SIZE))
        path = self.write_file(build_aax(checksum))
        self.assertEqual(read_file_checksum(path), checksum.hex())

    def test_finds_adrm_across_scan_chunk_boundary(self):
        checksum = b"\xab" * CHECKSUM_SIZE
        # pad the moov so the adrm atom lands past the first 1 MiB scan chunk
        padding = build_atom(b"free", b"\x00" * (1 << 20))
        path = self.write_file(build_aax(checksum, extra_moov=padding))
        self.assertEqual(read_file_checksum(path), checksum.hex())

    def test_handles_64_bit_atom_sizes(self):
        checksum = b"\xcd" * CHECKSUM_SIZE
        container = build_aax(checksum)
        ftyp_size = struct.unpack(">I", container[:4])[0]
        ftyp = container[:ftyp_size]
        # rewrite ftyp using the 64-bit size form
        large_ftyp = struct.pack(">I4sQ", 1, b"ftyp",
                                 len(ftyp) + 8) + ftyp[8:]
        path = self.write_file(large_ftyp + container[ftyp_size:])
        self.assertEqual(read_file_checksum(path), checksum.hex())

    def test_returns_none_without_adrm(self):
        path = self.write_file(build_atom(b"ftyp", b"isom") +
                               build_atom(b"moov", build_atom(b"mvhd", b"\x00" * 100)))
        self.assertIsNone(read_file_checksum(path))

    def test_returns_none_for_non_container(self):
        path = self.write_file(b"not an mp4 file at all")
        self.assertIsNone(read_file_checksum(path))


class ParseActivationCodeTests(unittest.TestCase):
    def test_parses_hex_line(self):
        output = (
            "plaintext of 0e6d891093b5feeff0ae690d4d357e33bf0a2319 is ????\n"
            "0e6d891093b5feeff0ae690d4d357e33bf0a2319  hex:d9e6d61d\n"
            "statistics\n"
        )
        self.assertEqual(parse_activation_code(output), "d9e6d61d")

    def test_ignores_lines_without_a_code(self):
        self.assertIsNone(parse_activation_code(
            "hex:\nno match found\n"))

    def test_returns_none_when_not_found(self):
        self.assertIsNone(parse_activation_code(
            "0 of 1 hashes cracked\n"))


if __name__ == "__main__":
    unittest.main()
