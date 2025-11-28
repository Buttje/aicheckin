import unittest

from vc_commit_helper.grouping.group_model import CommitGroup


class TestGroupModel(unittest.TestCase):
    def test_commit_group_dataclass(self) -> None:
        group = CommitGroup(type="feat", files=["a.py"], message="feat: add feature", diffs={"a.py": "diff"})
        self.assertEqual(group.type, "feat")
        self.assertEqual(group.files, ["a.py"])
        self.assertTrue(group.message.startswith("feat:"))
        self.assertEqual(group.diffs["a.py"], "diff")


if __name__ == "__main__":
    unittest.main()