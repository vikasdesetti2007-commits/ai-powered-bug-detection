"""Unit tests for the syntax and indentation error detector."""

import ast
import unittest
from bug_detector.analyzer.syntax_checker import check_syntax, format_pointer_diagram


class TestSyntaxChecker(unittest.TestCase):
    """Test suite for syntax validation and error extraction."""

    def test_valid_python_code(self):
        code = "def add(a, b):\n    return a + b\n"
        is_valid, err, tree = check_syntax(code)
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertIsInstance(tree, ast.AST)

    def test_empty_code_and_comments(self):
        code = "# Just a comment\n\n   \n"
        is_valid, err, tree = check_syntax(code)
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertIsInstance(tree, ast.AST)

    def test_syntax_error_missing_colon(self):
        code = "def bad_func(x)\n    return x\n"
        is_valid, err, tree = check_syntax(code)
        self.assertFalse(is_valid)
        self.assertIsNone(tree)
        self.assertIsNotNone(err)
        self.assertEqual(err.line_number, 1)
        self.assertIn("bad_func(x)", err.line_text)
        self.assertIn("^", err.pointer_diagram)

    def test_indentation_error(self):
        code = "def func():\nreturn 42\n"
        is_valid, err, tree = check_syntax(code)
        self.assertFalse(is_valid)
        self.assertIsNone(tree)
        self.assertIsNotNone(err)
        self.assertEqual(err.line_number, 2)
        self.assertIn("return 42", err.line_text)

    def test_unclosed_parenthesis(self):
        code = "total = (1 + 2\nprint('hello')"
        is_valid, err, tree = check_syntax(code)
        self.assertFalse(is_valid)
        self.assertIsNone(tree)
        self.assertIsNotNone(err)
        self.assertGreaterEqual(err.line_number, 1)

    def test_pointer_diagram_formatting(self):
        line = "x = [1, 2, 3"
        diagram = format_pointer_diagram(line, offset=13)
        self.assertIn("x = [1, 2, 3", diagram)
        self.assertTrue(diagram.endswith("^"))


if __name__ == "__main__":
    unittest.main()
