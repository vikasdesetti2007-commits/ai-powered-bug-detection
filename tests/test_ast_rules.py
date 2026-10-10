"""Unit tests for individual AST static bug detection rules."""

import ast
import unittest
from bug_detector.analyzer.rules.security import (
    EvalExecRule,
    UnsafeSubprocessRule,
    InsecureTempfileRule,
)
from bug_detector.analyzer.rules.correctness import (
    MutableDefaultArgRule,
    IdentityComparisonRule,
    DivisionByZeroRule,
    DuplicateDictKeysRule,
    UnreachableCodeRule,
)
from bug_detector.analyzer.rules.style import (
    BareExceptRule,
    ShadowedBuiltinsRule,
    AssertTupleRule,
)


class TestASTRules(unittest.TestCase):
    """Test suite covering individual AST rules for positive and negative cases."""

    def _analyze(self, rule_cls, code: str):
        tree = ast.parse(code)
        rule = rule_cls(source_code=code)
        return rule.analyze(tree)

    # SEC001: eval/exec
    def test_sec001_eval_exec_detected(self):
        code = "res = eval('2 + 2')\nexec('import os')\n"
        findings = self._analyze(EvalExecRule, code)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].rule_id, "SEC001")
        self.assertEqual(findings[1].rule_id, "SEC001")

    def test_sec001_clean_code(self):
        code = "import ast\nres = ast.literal_eval('{\"a\": 1}')\n"
        findings = self._analyze(EvalExecRule, code)
        self.assertEqual(len(findings), 0)

    # SEC002: unsafe subprocess & os.system
    def test_sec002_unsafe_subprocess_detected(self):
        code = "import os, subprocess\nos.system('rm -rf /')\nsubprocess.run('ls', shell=True)\n"
        findings = self._analyze(UnsafeSubprocessRule, code)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].rule_id, "SEC002")
        self.assertEqual(findings[1].rule_id, "SEC002")

    def test_sec002_safe_subprocess(self):
        code = "import subprocess\nsubprocess.run(['ls', '-la'], shell=False)\n"
        findings = self._analyze(UnsafeSubprocessRule, code)
        self.assertEqual(len(findings), 0)

    # SEC003: insecure tempfile.mktemp
    def test_sec003_tempfile_mktemp_detected(self):
        code = "import tempfile\ntemp_path = tempfile.mktemp()\n"
        findings = self._analyze(InsecureTempfileRule, code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "SEC003")

    def test_sec003_safe_tempfile(self):
        code = "import tempfile\nwith tempfile.NamedTemporaryFile() as f:\n    pass\n"
        findings = self._analyze(InsecureTempfileRule, code)
        self.assertEqual(len(findings), 0)

    # COR001: mutable default arguments
    def test_cor001_mutable_defaults_detected(self):
        code = "def append_val(x, arr=[], mapping={}, s=set()):\n    arr.append(x)\n"
        findings = self._analyze(MutableDefaultArgRule, code)
        self.assertEqual(len(findings), 3)
        self.assertTrue(all(f.rule_id == "COR001" for f in findings))

    def test_cor001_safe_defaults(self):
        code = "def append_val(x, arr=None):\n    if arr is None:\n        arr = []\n"
        findings = self._analyze(MutableDefaultArgRule, code)
        self.assertEqual(len(findings), 0)

    # COR002: identity comparison
    def test_cor002_identity_comparison_detected(self):
        code = "if val == None:\n    pass\nif flag == True:\n    pass\n"
        findings = self._analyze(IdentityComparisonRule, code)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f.rule_id == "COR002" for f in findings))

    def test_cor002_clean_comparison(self):
        code = "if val is None:\n    pass\nif flag:\n    pass\n"
        findings = self._analyze(IdentityComparisonRule, code)
        self.assertEqual(len(findings), 0)

    # COR003: division by zero
    def test_cor003_division_by_zero_detected(self):
        code = "a = 10 / 0\nb = 5 // 0\nc = 3 % 0.0\n"
        findings = self._analyze(DivisionByZeroRule, code)
        self.assertEqual(len(findings), 3)
        self.assertTrue(all(f.rule_id == "COR003" for f in findings))

    def test_cor003_valid_division(self):
        code = "a = 10 / 2\nb = 5 // 3\n"
        findings = self._analyze(DivisionByZeroRule, code)
        self.assertEqual(len(findings), 0)

    # COR004: duplicate dictionary keys
    def test_cor004_duplicate_dict_keys_detected(self):
        code = "data = {'key': 1, 'key': 2, 'other': 3}\n"
        findings = self._analyze(DuplicateDictKeysRule, code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "COR004")

    def test_cor004_clean_dict(self):
        code = "data = {'key1': 1, 'key2': 2}\n"
        findings = self._analyze(DuplicateDictKeysRule, code)
        self.assertEqual(len(findings), 0)

    # COR005: unreachable code
    def test_cor005_unreachable_code_detected(self):
        code = "def compute():\n    return 42\n    print('never reached')\n"
        findings = self._analyze(UnreachableCodeRule, code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "COR005")

    def test_cor005_reachable_code(self):
        code = "def compute(flag):\n    if flag:\n        return 1\n    return 0\n"
        findings = self._analyze(UnreachableCodeRule, code)
        self.assertEqual(len(findings), 0)

    # STY001: bare except
    def test_sty001_bare_except_detected(self):
        code = "try:\n    1 / 1\nexcept:\n    pass\n"
        findings = self._analyze(BareExceptRule, code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "STY001")

    def test_sty001_specific_except(self):
        code = "try:\n    1 / 1\nexcept ZeroDivisionError:\n    pass\n"
        findings = self._analyze(BareExceptRule, code)
        self.assertEqual(len(findings), 0)

    # STY002: shadowed builtins
    def test_sty002_shadowed_builtins_detected(self):
        code = "list = [1, 2, 3]\ndef process(id, type):\n    pass\n"
        findings = self._analyze(ShadowedBuiltinsRule, code)
        self.assertEqual(len(findings), 3)
        self.assertTrue(all(f.rule_id == "STY002" for f in findings))

    def test_sty002_clean_variable_names(self):
        code = "items = [1, 2, 3]\ndef process(item_id, item_type):\n    pass\n"
        findings = self._analyze(ShadowedBuiltinsRule, code)
        self.assertEqual(len(findings), 0)

    # STY003: assert tuple
    def test_sty003_assert_tuple_detected(self):
        code = "assert (x > 0, 'Must be positive')\n"
        findings = self._analyze(AssertTupleRule, code)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "STY003")

    def test_sty003_proper_assert(self):
        code = "assert x > 0, 'Must be positive'\n"
        findings = self._analyze(AssertTupleRule, code)
        self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()
