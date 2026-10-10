"""Unit tests for the CLI runner and terminal output."""

import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bug_detector.cli.main import run_cli


class TestCLI(unittest.TestCase):
    """Test suite for CLI interface."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "cli_history.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _build_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "file": None,
            "ai": False,
            "no_save": False,
            "json": False,
            "history": False,
            "history_limit": 10,
            "clear_history": False,
            "db_path": self.db_path,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_cli_clean_file(self):
        file_path = Path(self.temp_dir.name) / "clean.py"
        file_path.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")

        args = self._build_args(file=str(file_path))
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = run_cli(args)
            output = fake_out.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("No static bugs detected", output)

    def test_cli_file_with_bugs(self):
        file_path = Path(self.temp_dir.name) / "buggy.py"
        file_path.write_text("def bad(items=[]):\n    return 1 / 0\n")

        args = self._build_args(file=str(file_path))
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = run_cli(args)
            output = fake_out.getvalue()
            self.assertEqual(code, 1)  # Due to COR003 division by zero error severity
            self.assertIn("COR001", output)
            self.assertIn("COR003", output)

    def test_cli_syntax_error_file(self):
        file_path = Path(self.temp_dir.name) / "syntax_err.py"
        file_path.write_text("def broken(\n    return 1")

        args = self._build_args(file=str(file_path))
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = run_cli(args)
            output = fake_out.getvalue()
            self.assertEqual(code, 1)
            self.assertIn("SYNTAX ERROR", output)

    def test_cli_file_not_found(self):
        args = self._build_args(file="/nonexistent/path/script.py")
        with patch("sys.stderr", new=io.StringIO()) as fake_err:
            code = run_cli(args)
            self.assertEqual(code, 1)
            self.assertIn("File not found", fake_err.getvalue())

    def test_cli_directory_given_as_file(self):
        args = self._build_args(file=self.temp_dir.name)
        with patch("sys.stderr", new=io.StringIO()) as fake_err:
            code = run_cli(args)
            self.assertEqual(code, 1)
            self.assertIn("is a directory", fake_err.getvalue())

    def test_cli_json_output(self):
        file_path = Path(self.temp_dir.name) / "test_json.py"
        file_path.write_text("x = 42\n")

        args = self._build_args(file=str(file_path), json=True)
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = run_cli(args)
            self.assertEqual(code, 0)
            data = json.loads(fake_out.getvalue())
            self.assertTrue(data["is_syntax_valid"])
            self.assertIn("findings", data)
            self.assertIn("summary", data)

    def test_cli_history_and_clear(self):
        file_path = Path(self.temp_dir.name) / "sample.py"
        file_path.write_text("y = 100\n")

        # 1. Analyze to populate history
        run_cli(self._build_args(file=str(file_path)))

        # 2. Query history
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = run_cli(self._build_args(history=True))
            self.assertEqual(code, 0)
            self.assertIn("Review History", fake_out.getvalue())

        # 3. Clear history
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = run_cli(self._build_args(clear_history=True))
            self.assertEqual(code, 0)
            self.assertIn("Successfully cleared 1 records", fake_out.getvalue())


if __name__ == "__main__":
    unittest.main()
