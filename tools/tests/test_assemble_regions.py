"""Synthetic byte patterns only; no ROM data is needed."""

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import assemble_regions


class AssembleRegionsTests(unittest.TestCase):
    def test_program_interleaves_unswapped_words(self):
        self.assertEqual(assemble_regions.assemble_program_le(
            b"\x10\x11\x12\x13", b"\x20\x21\x22\x23"),
            b"\x10\x11\x20\x21\x12\x13\x22\x23")

    def test_byte_interleave_allows_odd_lengths(self):
        self.assertEqual(assemble_regions.interleave_bytes(b"abc", b"123"), b"a1b2c3")

    def test_swapping_words_is_an_involution(self):
        data = b"\x00\xff\x7f\x80"
        swapped = assemble_regions.swap_words(data)
        self.assertEqual(swapped, b"\xff\x00\x80\x7f")
        self.assertEqual(assemble_regions.swap_words(swapped), data)

    def test_empty_inputs(self):
        self.assertEqual(assemble_regions.assemble_program_le(b"", b""), b"")
        self.assertEqual(assemble_regions.interleave_bytes(b"", b""), b"")
        self.assertEqual(assemble_regions.swap_words(b""), b"")

    def test_invalid_lengths(self):
        for first, second in ((b"ab", b"abcd"), (b"a", b"b"), (b"", b"ab")):
            with self.subTest(first=first, second=second), self.assertRaises(ValueError):
                assemble_regions.assemble_program_le(first, second)
        with self.assertRaises(ValueError):
            assemble_regions.interleave_bytes(b"a", b"bc")
        with self.assertRaises(ValueError):
            assemble_regions.swap_words(b"abc")

    def test_output_outside_extracted_rejected_without_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(assemble_regions.inspect_rom, "inspect_archive") as inspect:
                with self.assertRaises(ValueError):
                    assemble_regions.assemble_regions("missing.zip", Path(temporary) / "output")
                inspect.assert_not_called()

    def test_validation_failure_creates_no_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            output = project / "extracted/regions"
            with mock.patch.object(assemble_regions, "PROJECT_ROOT", project), \
                    mock.patch.object(assemble_regions.inspect_rom, "inspect_archive",
                                      return_value={"ok": False}) as inspect:
                with self.assertRaises(ValueError):
                    assemble_regions.assemble_regions("missing.zip", output)
                inspect.assert_called_once()
            self.assertFalse(output.exists())

    def test_symlink_output_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            outside = Path(temporary) / "outside"
            project.mkdir()
            outside.mkdir()
            (project / "extracted").symlink_to(outside, target_is_directory=True)
            with mock.patch.object(assemble_regions, "PROJECT_ROOT", project):
                with self.assertRaises(ValueError):
                    assemble_regions.assemble_regions("missing.zip", project / "extracted/regions")


if __name__ == "__main__":
    unittest.main()
