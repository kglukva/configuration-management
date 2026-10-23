import csv
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

from src.main import VirtualFileSystem, execute_command


class TestStage4(unittest.TestCase):
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

        self.vfs = VirtualFileSystem(str(self.csv_path))

    def run_command(self, command, args):
        output = StringIO()
        with redirect_stdout(output):
            execute_command(command, args, self.vfs)
        return output.getvalue()

    def test_ls_lists_files(self):
        self.assertIn("readme.txt", self.run_command("ls", ["/docs"]))

    def test_cd_changes_directory(self):
        self.run_command("cd", ["/docs"])
        self.assertEqual(self.vfs.cwd, "/docs")

    def test_cd_missing_directory(self):
        self.assertIn("Error:", self.run_command("cd", ["/missing"]))

    def test_rev_reverses_file(self):
        self.assertEqual(self.run_command("rev", ["/docs/readme.txt"]), "EDCBA\n")

    def test_history_command(self):
        self.vfs.history.append("ls /")
        self.assertIn("ls /", self.run_command("history", []))


if __name__ == "__main__":
    unittest.main()
