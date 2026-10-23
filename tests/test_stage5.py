import csv
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

from src.main import VirtualFileSystem, execute_command


class TestStage5(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / "vfs.csv"

        with self.csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["path", "type", "content"])
            writer.writerow(["/", "dir", ""])
            writer.writerow(["/docs", "dir", ""])
            writer.writerow(["/docs/readme.txt", "file", "Hello"])
            writer.writerow(["/empty", "dir", ""])

        self.vfs = VirtualFileSystem(str(self.csv_path))

    def run_command(self, command, args):
        output = StringIO()
        with redirect_stdout(output):
            execute_command(command, args, self.vfs)
        return output.getvalue()

    def test_rmdir_empty_directory(self):
        self.run_command("rmdir", ["/empty"])
        self.assertNotIn("/empty", self.vfs.entries)

    def test_rmdir_rejects_nonempty_directory(self):
        output = self.run_command("rmdir", ["/docs"])
        self.assertIn("Error:", output)
        self.assertIn("/docs", self.vfs.entries)

    def test_rmdir_rejects_root(self):
        output = self.run_command("rmdir", ["/"])
        self.assertIn("Error:", output)
        self.assertIn("/", self.vfs.entries)

    def test_cp_copies_file_in_memory(self):
        original_csv = self.csv_path.read_bytes()
        self.run_command("cp", ["/docs/readme.txt", "/docs/copy.txt"])
        self.assertEqual(self.vfs.read_file("/docs/copy.txt"), "Hello")
        self.assertEqual(self.csv_path.read_bytes(), original_csv)

    def test_cp_rejects_missing_source(self):
        output = self.run_command("cp", ["/missing.txt", "/docs/copy.txt"])
        self.assertIn("Error:", output)
        self.assertNotIn("/docs/copy.txt", self.vfs.entries)


if __name__ == "__main__":
    unittest.main()
