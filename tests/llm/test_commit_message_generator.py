import unittest
from types import SimpleNamespace

from vc_commit_helper.grouping.group_model import CommitGroup
from vc_commit_helper.llm.commit_message_generator import CommitMessageGenerator
from vc_commit_helper.llm.ollama_client import LLMError


class DummyLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
    def generate(self, prompt):
        self.calls.append(prompt)
        if not self.responses:
            raise LLMError("No response")
        return self.responses.pop(0)


class TestCommitMessageGenerator(unittest.TestCase):
    def test_generate_groups_with_llm(self) -> None:
        responses = [
            "feat: add feature\n\n- a.py",
            "docs: update docs\n\n- README.md",
        ]
        llm = DummyLLM(responses)
        generator = CommitMessageGenerator(llm)
        diffs = {
            "a.py": "+def foo():\n+    pass\n",
            "README.md": "+Added docs\n",
        }
        groups = generator.generate_groups(diffs)
        self.assertEqual(len(groups), 2)
        types_set = {g.type for g in groups}
        self.assertEqual(types_set, {"feat", "docs"})
        for g in groups:
            self.assertTrue(g.message.splitlines()[0].startswith(g.type))

    def test_generate_groups_fallback(self) -> None:
        llm = DummyLLM(responses=[])
        generator = CommitMessageGenerator(llm)
        diffs = {"script.py": "+# bugfix\n"}
        groups = generator.generate_groups(diffs)
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertTrue(g.message.startswith(f"{g.type}:"))


if __name__ == "__main__":
    unittest.main()