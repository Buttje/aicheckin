import unittest

from vc_commit_helper.grouping.change_classifier import classify_change


class TestChangeClassifier(unittest.TestCase):
    def test_classify_change_cases(self) -> None:
        cases = [
            ("README.md", "", "docs"),
            ("tests/test_example.py", "", "test"),
            (".github/workflows/ci.yml", "", "ci"),
            ("Dockerfile", "", "build"),
            ("module.py", "+# New feature\n", "feat"),
            ("module.py", "+# fix bug\n", "fix"),
            ("module.py", "-    x=1\n+    x = 1\n", "style"),
            ("unknown.bin", "", "other"),
        ]
        for file_path, diff, expected in cases:
            with self.subTest(file=file_path):
                self.assertEqual(classify_change(file_path, diff), expected)


if __name__ == "__main__":
    unittest.main()