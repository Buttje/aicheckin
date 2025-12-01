"""Comprehensive tests for change classifier."""

import unittest

from vc_commit_helper.grouping.change_classifier import classify_change


class TestChangeClassifierComprehensive(unittest.TestCase):
    """Comprehensive tests for change classification."""

    def test_classify_docs_extensions(self):
        """Test documentation file classification."""
        test_cases = [
            ("README.md", "docs"),
            ("CHANGELOG.rst", "docs"),
            ("notes.txt", "docs"),
            ("guide.adoc", "docs"),
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file=file_path):
                result = classify_change(file_path, "")
                self.assertEqual(result, expected)

    def test_classify_test_files(self):
        """Test test file classification."""
        test_cases = [
            ("test_module.py", "test"),
            ("module_test.py", "test"),
            ("tests/test_feature.py", "test"),
            ("src/tests/unit/test_api.py", "test"),
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file=file_path):
                result = classify_change(file_path, "")
                self.assertEqual(result, expected)

    def test_classify_build_files(self):
        """Test build file classification."""
        test_cases = [
            ("Dockerfile", "build"),
            ("docker-compose.yml", "build"),
            ("setup.yaml", "build"),
        ]
        
        for file_path, expected in test_cases:
            with self.subTest(file=file_path):
                result = classify_change(file_path, "")
                self.assertEqual(result, expected)

    def test_classify_ci_files(self):
        """Test CI file classification."""
        result = classify_change(".github/workflows/ci.yml", "")
        self.assertEqual(result, "ci")

    def test_classify_style_whitespace_only(self):
        """Test style classification for whitespace-only changes."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
-def foo():
+def foo( ):
-    pass
+     pass
"""
        result = classify_change("file.py", diff)
        self.assertEqual(result, "style")

    def test_classify_style_blank_lines(self):
        """Test style classification for blank line changes."""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,3 @@
 def foo():
+
     pass
"""
        result = classify_change("file.py", diff)
        self.assertEqual(result, "style")

    def test_classify_fix_keywords(self):
        """Test fix classification based on keywords."""
        keywords = ["fix", "fixed", "bug", "error", "issue", "patch", "hotfix"]
        
        for keyword in keywords:
            with self.subTest(keyword=keyword):
                diff = f"+# {keyword} the problem"
                result = classify_change("module.py", diff)
                self.assertEqual(result, "fix")

    def test_classify_refactor(self):
        """Test refactor classification."""
        diff = "+# refactor this code"
        result = classify_change("module.py", diff)
        self.assertEqual(result, "refactor")

    def test_classify_perf(self):
        """Test performance classification."""
        test_cases = [
            "+# improve performance",
            "+# perf optimization",
        ]
        
        for diff in test_cases:
            with self.subTest(diff=diff):
                result = classify_change("module.py", diff)
                self.assertEqual(result, "perf")

    def test_classify_feat_keyword(self):
        """Test feature classification by keyword."""
        diff = "+# add new feature"
        result = classify_change("module.py", diff)
        self.assertEqual(result, "feat")

    def test_classify_feat_new_code(self):
        """Test feature classification by new code structures."""
        test_cases = [
            "+class NewClass:",
            "+def new_function():",
            "+function newFunc() {",
        ]
        
        for diff in test_cases:
            with self.subTest(diff=diff):
                result = classify_change("module.py", diff)
                self.assertEqual(result, "feat")

    def test_classify_other_fallback(self):
        """Test fallback to 'other' classification."""
        diff = "+# some random change"
        result = classify_change("unknown.bin", diff)
        self.assertEqual(result, "other")

    def test_classify_empty_diff(self):
        """Test classification with empty diff."""
        result = classify_change("module.py", "")
        self.assertEqual(result, "other")