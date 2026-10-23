import unittest
from unittest.mock import patch
from io import StringIO
from contextlib import redirect_stdout

from src.main import parse_command, execute_command


class TestParseCommand(unittest.TestCase):

    def test_simple_command(self):
        self.assertEqual(
            parse_command("ls /tmp"),
            ("ls", ["/tmp"])
        )

    def test_empty_command(self):
        self.assertEqual(
            parse_command(""),
            (None, [])
        )

    def test_environment_variable(self):
        with patch.dict("os.environ", {"TEST_DIR": "/home/test"}):
            self.assertEqual(
                parse_command("ls $TEST_DIR"),
                ("ls", ["/home/test"])
            )

    def test_quoted_argument(self):
        self.assertEqual(
            parse_command('ls "hello world"'),
            ("ls", ["hello world"])
        )

    def test_invalid_quotes(self):
        with self.assertRaises(ValueError):
            parse_command('ls "hello')


class TestExecuteCommand(unittest.TestCase):

    def test_ls(self):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command("ls", ["/tmp"])

        self.assertTrue(result)
        self.assertIn("ls", output.getvalue())
        self.assertIn("/tmp", output.getvalue())

    def test_cd(self):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command("cd", ["/tmp"])

        self.assertTrue(result)
        self.assertIn("cd", output.getvalue())

    def test_unknown_command(self):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command("hello", [])

        self.assertTrue(result)
        self.assertIn("unknown command", output.getvalue())

    def test_exit(self):
        self.assertFalse(execute_command("exit", []))

    def test_exit_with_arguments(self):
        output = StringIO()
        with redirect_stdout(output):
            result = execute_command("exit", ["test"])

        self.assertTrue(result)
        self.assertIn("does not accept arguments", output.getvalue())


if __name__ == "__main__":
    unittest.main()
