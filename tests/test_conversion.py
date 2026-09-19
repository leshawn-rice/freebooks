"""Conversion tests that run against whichever ffmpeg FreeBooks resolves.

These exercise the real binary the package depends on (the bundled
imageio-ffmpeg build, unless FREEBOOKS_FFMPEG or PATH provides another one),
rather than assuming a system ffmpeg is installed.
"""

import os
import shutil
import subprocess as sp
import sys
import tempfile
import unittest
from unittest import mock

from freebooks import ffmpeg as ffmpeg_module
from freebooks import main as fb
from freebooks.aax import read_file_checksum

# Set FREEBOOKS_TEST_AAX to a real .aax file to enable the end-to-end tests.
# "~" and $VARS are expanded, so a quoted path still works.
TEST_AAX = os.environ.get("FREEBOOKS_TEST_AAX")
if TEST_AAX:
    TEST_AAX = os.path.abspath(
        os.path.expanduser(os.path.expandvars(TEST_AAX)))
    if not os.path.isfile(TEST_AAX):
        print(f"warning: FREEBOOKS_TEST_AAX does not exist: {TEST_AAX}",
              file=sys.stderr)
        TEST_AAX = None

FFMPEG = ffmpeg_module.find_ffmpeg()


@unittest.skipIf(FFMPEG is None, "no ffmpeg available")
class ResolvedFFmpegTests(unittest.TestCase):
    """The resolved binary must actually be able to do the job."""

    def run_ffmpeg(self, *args):
        return sp.run([FFMPEG, "-hide_banner", *args],
                      stdout=sp.PIPE, stderr=sp.STDOUT, check=True).stdout.decode()

    def test_supports_every_advertised_output_format(self):
        encoders = self.run_ffmpeg("-encoders")
        for codec in ("libmp3lame", "aac", "flac", "libopus", "pcm_s16le"):
            self.assertIn(codec, encoders, f"{FFMPEG} cannot encode {codec}")

    def test_supports_aax_activation_bytes(self):
        self.assertIn("activation_bytes", self.run_ffmpeg("-h", "demuxer=mov"))

    def test_prefers_system_ffmpeg_when_installed(self):
        """A distribution's ffmpeg is patched, so it wins over the bundled one."""
        system = shutil.which("ffmpeg")
        if not system:
            self.skipTest("no ffmpeg on PATH")
        self.assertEqual(ffmpeg_module.find_ffmpeg(), system)

    def test_falls_back_to_the_bundled_build(self):
        try:
            import imageio_ffmpeg
        except ImportError:
            self.skipTest("imageio-ffmpeg is not installed")

        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/nonexistent"
        self.addCleanup(os.environ.__setitem__, "PATH", original_path)

        self.assertEqual(ffmpeg_module.find_ffmpeg(),
                         imageio_ffmpeg.get_ffmpeg_exe())

    def test_environment_override_wins(self):
        os.environ[ffmpeg_module.FFMPEG_ENV_VAR] = FFMPEG
        self.addCleanup(os.environ.pop, ffmpeg_module.FFMPEG_ENV_VAR, None)
        self.assertEqual(ffmpeg_module.find_ffmpeg(), FFMPEG)

    def test_reports_missing_binary_clearly(self):
        os.environ[ffmpeg_module.FFMPEG_ENV_VAR] = "/nonexistent/ffmpeg"
        self.addCleanup(os.environ.pop, ffmpeg_module.FFMPEG_ENV_VAR, None)
        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/nonexistent"
        self.addCleanup(os.environ.__setitem__, "PATH", original_path)

        bundled = ffmpeg_module._bundled_ffmpeg()
        if bundled:
            self.skipTest("bundled ffmpeg is installed, so none is missing")
        with self.assertRaises(RuntimeError):
            ffmpeg_module.get_ffmpeg()


@unittest.skipIf(FFMPEG is None, "no ffmpeg available")
class ConvertFileTests(unittest.TestCase):
    """convert_file() drives the resolved ffmpeg for every supported format."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="freebooks-test-")
        cls.source = os.path.join(cls.tmpdir, "source.m4a")
        sp.run(
            [FFMPEG, "-y", "-v", "error", "-f", "lavfi",
             "-i", "sine=frequency=440:duration=2", "-c:a", "aac", cls.source],
            check=True,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def convert(self, file_type):
        output = os.path.join(self.tmpdir, f"out.{file_type}")
        fb.convert_file(self.source, output, "deadbeef", file_type)
        return output

    def assert_decodable(self, path):
        self.assertTrue(os.path.getsize(path) > 0, f"{path} is empty")
        sp.run([FFMPEG, "-v", "error", "-i", path, "-f", "null", "-"],
               check=True, stdout=sp.DEVNULL, stderr=sp.PIPE)

    def stream_description(self, path):
        """Read the decoded stream line ffmpeg prints, without needing ffprobe."""
        probe = sp.run([FFMPEG, "-hide_banner", "-i", path],
                       stdout=sp.DEVNULL, stderr=sp.PIPE, check=False)
        for line in probe.stderr.decode(errors="replace").splitlines():
            if "Audio:" in line:
                return line
        return ""

    def test_converts_each_supported_format(self):
        expected_codecs = {
            "mp3": "mp3",
            "m4a": "aac",
            "flac": "flac",
            "wav": "pcm_s16le",
            "opus": "opus",
        }
        for file_type, codec in expected_codecs.items():
            with self.subTest(file_type=file_type):
                output = self.convert(file_type)
                self.assert_decodable(output)
                self.assertIn(f"Audio: {codec}",
                              self.stream_description(output))

    def test_opus_uses_a_bitrate_not_a_quality_scale(self):
        """libopus rejects -q:a, so the opus branch must pass a bitrate."""
        with mock.patch.object(fb.sp, "run") as runner:
            fb.convert_file("in.aax", "out.opus", "deadbeef", "opus")
        command = runner.call_args[0][0]
        self.assertIn("-b:a", command)
        self.assertNotIn("-q:a", command)

    def test_lossless_formats_get_no_quality_flag(self):
        for file_type in ("flac", "wav"):
            with self.subTest(file_type=file_type):
                with mock.patch.object(fb.sp, "run") as runner:
                    fb.convert_file("in.aax", f"out.{file_type}",
                                    "deadbeef", file_type)
                self.assertNotIn("-q:a", runner.call_args[0][0])

    def test_unknown_format_falls_back_to_ffmpeg_defaults(self):
        with mock.patch.object(fb.sp, "run") as runner:
            fb.convert_file("in.aax", "out.ogg", "deadbeef", "ogg")
        command = runner.call_args[0][0]
        self.assertNotIn("-c:a", command)
        self.assertEqual(command[-1], "out.ogg")

    def test_output_type_falls_back_to_the_file_extension(self):
        with mock.patch.object(fb.sp, "run") as runner:
            fb.convert_file("in.aax", "out.flac", "deadbeef", None)
        command = runner.call_args[0][0]
        self.assertIn("flac", command)

    def test_activation_bytes_are_passed_to_ffmpeg(self):
        with mock.patch.object(fb.sp, "run") as runner:
            fb.convert_file("in.aax", "out.mp3", "d9e6d61d", "mp3")
        command = runner.call_args[0][0]
        self.assertIn("-activation_bytes", command)
        self.assertEqual(command[command.index("-activation_bytes") + 1],
                         "d9e6d61d")

    def test_raises_on_ffmpeg_failure(self):
        missing = os.path.join(self.tmpdir, "does-not-exist.aax")
        with self.assertRaises(RuntimeError):
            fb.convert_file(missing, os.path.join(
                self.tmpdir, "bad.mp3"), "deadbeef", "mp3")


@unittest.skipIf(not TEST_AAX, "set FREEBOOKS_TEST_AAX to run end-to-end tests")
@unittest.skipIf(FFMPEG is None, "no ffmpeg available")
class RealAaxTests(unittest.TestCase):
    """Cross-check the pure-Python reader against the ffmpeg we depend on."""

    def test_checksum_matches_ffmpeg(self):
        self.assertEqual(read_file_checksum(TEST_AAX),
                         fb._checksum_via_ffmpeg(TEST_AAX))

    def test_full_pipeline_produces_playable_audio(self):
        checksum = fb.get_file_checksum(TEST_AAX)
        activation_code = fb.get_activation_code(TEST_AAX, checksum)

        tmpdir = tempfile.mkdtemp(prefix="freebooks-e2e-")
        self.addCleanup(shutil.rmtree, tmpdir, True)
        output = os.path.join(tmpdir, "out.mp3")

        fb.convert_file(TEST_AAX, output, activation_code, "mp3")
        sp.run([FFMPEG, "-v", "error", "-i", output, "-f", "null", "-"],
               check=True, stdout=sp.DEVNULL, stderr=sp.PIPE)


if __name__ == "__main__":
    unittest.main()
