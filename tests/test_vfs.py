
import csv
import hashlib
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from src.main import VirtualFileSystem, execute_command


class TestVirtualFileSystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.csv_path = Path(self.temp_dir.name) / "test_vfs.csv"

        with self.csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["path", "type", "content"])
            writer.writerow(["/", "dir", ""])
            writer.writerow(["/docs", "dir", ""])
            writer.writerow(["/docs/readme.txt", "file", "Hello"])
            writer.writerow(["/empty", "dir", ""])
            writer.writerow(["/deep", "dir", ""])
            writer.writerow(["/deep/level", "dir", ""])
            writer.writerow(["/deep/level/data.txt", "file", "ABC"])

        self.vfs = VirtualFileSystem(str(self.csv_path))

    def test_loads_files_and_directories(self):
        self.assertEqual(self.vfs.read_file("/docs/readme.txt"), "Hello")
        self.assertEqual(self.vfs.list_dir("/empty"), [])
        self.assertIn("docs/", self.vfs.list_dir("/"))

    def test_supports_nested_directories(self):
        self.assertEqual(
            self.vfs.read_file("/deep/level/data.txt"),
            "ABC",
        )

    def test_calculates_sha256(self):
        expected = hashlib.sha256(self.csv_path.read_bytes()).hexdigest()
        self.assertEqual(self.vfs.sha256, expected)

    def test_vfs_info_command(self):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command("vfs-info", [], self.vfs)

        self.assertTrue(result)
        self.assertIn(self.vfs.name, output.getvalue())
        self.assertIn(self.vfs.sha256, output.getvalue())

    def test_missing_path_reports_error(self):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command("ls", ["/missing"], self.vfs)

        self.assertTrue(result)
        self.assertIn("Error:", output.getvalue())

    def test_rejects_missing_parent_directory(self):
        bad_csv = Path(self.temp_dir.name) / "bad.csv"
        bad_csv.write_text(
            "path,type,content\n"
            "/,dir,\n"
            "/missing/file.txt,file,content\n",
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            VirtualFileSystem(str(bad_csv))


if __name__ == "__main__":
    unittest.main()

