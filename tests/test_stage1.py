import unittest
from src.main import parse_command, execute_command
from contextlib import redirect_stdout
from io import StringIO


class TestStage1(unittest.TestCase):
    def test_simple_command(self):
        self.assertEqual(parse_command("ls /"), ("ls", ["/"]))

    def test_empty_command(self):
        self.assertEqual(parse_command(""), (None, []))

    def test_environment_variable(self):
        command, args = parse_command("echo $HOME")
        self.assertEqual(command, "echo")
        self.assertTrue(args[0])

    def test_quoted_argument(self):
        self.assertEqual(
            parse_command('echo "hello world"'),
            ("echo", ["hello world"]),
        )

    def test_invalid_quotes(self):
        with self.assertRaises(ValueError):
            parse_command('echo "hello')

    def test_unknown_command(self):
        output = StringIO()
        with redirect_stdout(output):
            execute_command("unknown", [], None)
        self.assertIn("Error:", output.getvalue())

    def test_exit(self):
        self.assertFalse(execute_command("exit", [], None))

    def test_ls_stub(self):
        output = StringIO()
        with redirect_stdout(output):
            execute_command("ls", ["/"], None)
        self.assertIn("ls", output.getvalue())

    def test_cd_stub(self):
        output = StringIO()
        with redirect_stdout(output):
            execute_command("cd", ["/tmp"], None)
        self.assertIn("cd", output.getvalue())


if __name__ == "__main__":
    unittest.main()
