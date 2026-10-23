
import csv
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from src.main import VirtualFileSystem, execute_command


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / "vfs.csv"

        with self.csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["path", "type", "content"])
            writer.writerow(["/", "dir", ""])
            writer.writerow(["/docs", "dir", ""])
            writer.writerow(["/docs/readme.txt", "file", "ABCDE"])
            writer.writerow(["/empty", "dir", ""])

        self.vfs = VirtualFileSystem(str(self.csv_path))

    def run_command(self, command, args):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command(command, args, self.vfs)
        return result, output.getvalue()

    def test_ls_lists_directory(self):
        _, output = self.run_command("ls", ["/docs"])
        self.assertIn("readme.txt", output)

    def test_cd_changes_directory(self):
        self.run_command("cd", ["/docs"])
        self.assertEqual(self.vfs.cwd, "/docs")

    def test_cd_rejects_missing_directory(self):
        _, output = self.run_command("cd", ["/missing"])
        self.assertIn("Error:", output)
        self.assertEqual(self.vfs.cwd, "/")

    def test_rev_reverses_file(self):
        _, output = self.run_command("rev", ["/docs/readme.txt"])
        self.assertEqual(output, "EDCBA\n")

    def test_rev_without_file_reverses_last_history_entry(self):
        self.vfs.history.append("hello")
        _, output = self.run_command("rev", [])
        self.assertEqual(output, "olleh\n")

    def test_rmdir_removes_empty_directory(self):
        _, output = self.run_command("rmdir", ["/empty"])
        self.assertNotIn("/empty", self.vfs.entries)
        self.assertIn("Removed directory", output)

    def test_rmdir_rejects_nonempty_directory(self):
        _, output = self.run_command("rmdir", ["/docs"])
        self.assertIn("Error:", output)
        self.assertIn("/docs", self.vfs.entries)

    def test_rmdir_cannot_remove_root(self):
        _, output = self.run_command("rmdir", ["/"])
        self.assertIn("Error:", output)
        self.assertIn("/", self.vfs.entries)

    def test_cp_copies_file_in_memory(self):
        original_csv = self.csv_path.read_bytes()
        _, output = self.run_command(
            "cp", ["/docs/readme.txt", "/docs/copy.txt"]
        )

        self.assertEqual(self.vfs.read_file("/docs/copy.txt"), "ABCDE")
        self.assertEqual(self.csv_path.read_bytes(), original_csv)
        self.assertIn("Copied", output)

    def test_cp_rejects_missing_source(self):
        _, output = self.run_command(
            "cp", ["/missing.txt", "/docs/copy.txt"]
        )
        self.assertIn("Error:", output)
        self.assertNotIn("/docs/copy.txt", self.vfs.entries)

    def test_cp_rejects_existing_destination(self):
        _, output = self.run_command(
            "cp", ["/docs/readme.txt", "/docs/readme.txt"]
        )
        self.assertIn("Error:", output)

    def test_cp_to_directory(self):
        self.run_command("cp", ["/docs/readme.txt", "/"])
        self.assertEqual(self.vfs.read_file("/readme.txt"), "ABCDE")


if __name__ == "__main__":
    unittest.main()

