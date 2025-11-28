import unittest
from types import SimpleNamespace

from vc_commit_helper.diff.diff_extractor import extract_diffs


class DummyClient:
    def __init__(self):
        self.calls = []

    def get_diff(self, path):
        self.calls.append(path)
        return f"diff for {path}"


class TestDiffExtractor(unittest.TestCase):
    def test_extract_diffs_collects_all(self) -> None:
        client = DummyClient()
        changes = [SimpleNamespace(path="a.txt"), SimpleNamespace(path="b.py")]
        diffs = extract_diffs(client, changes)
        self.assertEqual(diffs, {"a.txt": "diff for a.txt", "b.py": "diff for b.py"})
        self.assertEqual(client.calls, ["a.txt", "b.py"])


if __name__ == "__main__":
    unittest.main()