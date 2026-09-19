"""Tests for the CLI surface, argument handling and orchestration."""

import os
import subprocess as sp
import sys
import tempfile
import unittest
from unittest import mock

from freebooks import ffmpeg as ffmpeg_module
from freebooks import main as fb

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ArgumentParsingTests(unittest.TestCase):
    def parse(self, *argv):
        with mock.patch.object(sys, "argv", ["freebooks", *argv]):
            return fb.parse_cli_arguments()

    def test_defaults(self):
        args = self.parse("book.aax")
        self.assertEqual(args.filename, "book.aax")
        self.assertEqual(args.output_file, "output.mp3")
        self.assertEqual(args.output_type, "mp3")
        self.assertFalse(args.force)
        self.assertFalse(args.verbose)

    def test_all_options(self):
        args = self.parse("book.aax", "-o", "out.flac",
                          "-t", "flac", "-f", "-v")
        self.assertEqual(args.output_file, "out.flac")
        self.assertEqual(args.output_type, "flac")
        self.assertTrue(args.force)
        self.assertTrue(args.verbose)

    def test_every_advertised_format_is_accepted(self):
        for file_type in ("mp3", "m4a", "flac", "wav", "opus"):
            with self.subTest(file_type=file_type):
                self.assertEqual(
                    self.parse("book.aax", "-t", file_type).output_type, file_type)

    def test_rejects_unknown_format(self):
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            self.parse("book.aax", "-t", "ogg")

    def test_requires_an_input_file(self):
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            self.parse()


class InputPathTests(unittest.TestCase):
    def test_resolves_relative_path(self):
        handle = tempfile.NamedTemporaryFile(suffix=".aax", delete=False)
        handle.close()
        self.addCleanup(os.unlink, handle.name)

        directory, name = os.path.split(handle.name)
        cwd = os.getcwd()
        os.chdir(directory)
        self.addCleanup(os.chdir, cwd)

        self.assertEqual(fb.get_input_path(name), handle.name)

    def test_rejects_missing_file(self):
        with self.assertRaises(ValueError):
            fb.get_input_path("/nonexistent/book.aax")


class DependencyCheckTests(unittest.TestCase):
    def test_passes_with_a_usable_environment(self):
        if ffmpeg_module.find_ffmpeg() is None:
            self.skipTest("no ffmpeg available")
        fb.check_external_tools()  # must not raise or exit

    def test_exits_when_ffmpeg_is_missing(self):
        with mock.patch.object(fb, "get_ffmpeg", side_effect=RuntimeError("no ffmpeg")):
            with self.assertRaises(SystemExit) as caught:
                fb.check_external_tools()
        self.assertEqual(caught.exception.code, 1)

    def test_exits_when_rcrack_is_missing(self):
        with mock.patch.object(fb, "rcrack", "/nonexistent/rcrack"):
            with self.assertRaises(SystemExit) as caught:
                fb.check_external_tools()
        self.assertEqual(caught.exception.code, 1)


class ProcessConversionTests(unittest.TestCase):
    """The orchestration layer, with the expensive steps stubbed out."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="freebooks-cli-")
        self.addCleanup(lambda: __import__("shutil").rmtree(
            self.tmpdir, ignore_errors=True))

        self.source = os.path.join(self.tmpdir, "book.aax")
        with open(self.source, "wb") as handle:
            handle.write(b"\x00" * 16)

        patches = {
            "check_external_tools": None,
            "get_file_checksum": "0e6d891093b5feeff0ae690d4d357e33bf0a2319",
            "get_activation_code": "d9e6d61d",
            "convert_file": None,
        }
        self.mocks = {}
        for name, return_value in patches.items():
            patcher = mock.patch.object(fb, name, return_value=return_value)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def test_runs_the_pipeline_in_order(self):
        output = os.path.join(self.tmpdir, "out.mp3")
        fb.convert_aax_to_audio(self.source, output, "mp3")

        self.mocks["check_external_tools"].assert_called_once()
        self.mocks["get_file_checksum"].assert_called_once_with(self.source)
        self.mocks["get_activation_code"].assert_called_once_with(
            self.source, "0e6d891093b5feeff0ae690d4d357e33bf0a2319")
        self.mocks["convert_file"].assert_called_once_with(
            self.source, output, "d9e6d61d", "mp3")

    def test_refuses_to_overwrite_without_force(self):
        output = os.path.join(self.tmpdir, "existing.mp3")
        open(output, "wb").close()

        with self.assertRaises(ValueError):
            fb.convert_aax_to_audio(self.source, output, "mp3")
        self.mocks["convert_file"].assert_not_called()

    def test_overwrites_with_force(self):
        output = os.path.join(self.tmpdir, "existing.mp3")
        open(output, "wb").close()

        fb.convert_aax_to_audio(self.source, output, "mp3", force=True)
        self.mocks["convert_file"].assert_called_once()

    def test_rejects_missing_input(self):
        with self.assertRaises(ValueError):
            fb.convert_aax_to_audio(os.path.join(self.tmpdir, "gone.aax"),
                                    os.path.join(self.tmpdir, "out.mp3"))

    def test_verbose_flag_enables_debug_logging(self):
        fb.convert_aax_to_audio(self.source, os.path.join(self.tmpdir, "v.mp3"),
                                verbose=True)
        self.assertEqual(fb.log.logger.level, 10)  # logging.DEBUG


class ConsoleEntryPointTests(unittest.TestCase):
    """Drive the tool the way a user does, as a separate process."""

    def run_cli(self, *argv):
        return sp.run(
            [sys.executable, "-c",
             "from freebooks.main import main; main()", *argv],
            cwd=REPO_ROOT, stdout=sp.PIPE, stderr=sp.STDOUT)

    def test_help_lists_the_options(self):
        result = self.run_cli("--help")
        output = result.stdout.decode()
        self.assertEqual(result.returncode, 0)
        for fragment in ("INPUT_FILE", "--output-file", "--output-type", "--force", "--verbose"):
            self.assertIn(fragment, output)

    def test_missing_input_file_fails_cleanly(self):
        result = self.run_cli("/nonexistent/book.aax")
        output = result.stdout.decode()
        self.assertNotEqual(result.returncode, 0)

        if ffmpeg_module.find_ffmpeg() is None:
            # the dependency check runs first, so that is what the user sees
            self.assertIn("No ffmpeg binary available", output)
        else:
            self.assertIn("Invalid file path", output)

    def test_rejects_unknown_format(self):
        result = self.run_cli("book.aax", "-t", "ogg")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stdout.decode())


class ChecksumFailureTests(unittest.TestCase):
    def test_non_aax_input_raises(self):
        if ffmpeg_module.find_ffmpeg() is None:
            self.skipTest("no ffmpeg available")

        handle = tempfile.NamedTemporaryFile(suffix=".aax", delete=False)
        handle.write(b"definitely not an audio file")
        handle.close()
        self.addCleanup(os.unlink, handle.name)

        with self.assertRaises(RuntimeError):
            fb.get_file_checksum(handle.name)

    def test_unmatched_checksum_raises(self):
        with mock.patch.object(fb.sp, "run") as runner:
            runner.return_value = mock.Mock(stdout=b"0 of 1 hashes cracked\n")
            with self.assertRaises(RuntimeError):
                fb.get_activation_code("book.aax", "0" * 40)


if __name__ == "__main__":
    unittest.main()
