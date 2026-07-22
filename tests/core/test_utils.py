from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from core.utils import (
    ensure_directory_exists,
    format_bytes,
    generate_uuid,
    is_json_serializable,
    read_json_file,
    safe_filename,
    truncate_text,
    write_json_file,
)


class CoreUtilsTests(SimpleTestCase):

    def test_generate_uuid(self):
        value = generate_uuid()

        self.assertEqual(
            len(value),
            36,
        )

    def test_safe_filename(self):
        self.assertEqual(
            safe_filename(
                'test<>:"file?.json'
            ),
            "test____file_.json",
        )

    def test_truncate_text(self):
        self.assertEqual(
            truncate_text(
                "abcdefghij",
                5,
            ),
            "ab...",
        )

    def test_json_roundtrip(self):

        with TemporaryDirectory() as tmp:

            path = (
                Path(tmp)
                / "test.json"
            )

            data = {
                "name": "Digital Twin",
                "version": 1,
            }

            write_json_file(
                path,
                data,
            )

            loaded = read_json_file(
                path,
            )

            self.assertEqual(
                loaded,
                data,
            )

    def test_directory_creation(self):

        with TemporaryDirectory() as tmp:

            directory = (
                Path(tmp)
                / "nested"
                / "folder"
            )

            ensure_directory_exists(
                directory,
            )

            self.assertTrue(
                directory.exists()
            )

    def test_json_serializable(self):

        self.assertTrue(
            is_json_serializable(
                {"a": 1}
            )
        )

    def test_non_json_serializable(self):

        class Dummy:
            pass

        self.assertFalse(
            is_json_serializable(
                Dummy()
            )
        )

    def test_format_bytes(self):

        self.assertEqual(
            format_bytes(
                1024,
            ),
            "1.00 KB",
        )
