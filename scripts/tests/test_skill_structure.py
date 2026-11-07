"""Packaging checks and regressions for executable documentation examples.

These checks do not evaluate model understanding or instruction compliance.
"""
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class SkillStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\n(.*?)\n---", cls.skill_text, re.DOTALL)
        if frontmatter is None:
            raise AssertionError("SKILL.md frontmatter is missing")
        cls.metadata = yaml.safe_load(frontmatter.group(1))
        cls.resource_paths = set(
            re.findall(r"`((?:references|scripts)/[^`\s]+)`", cls.skill_text)
        )

    def test_metadata_is_usable_for_discovery(self):
        self.assertEqual(
            self.metadata["name"], "cpp-hpc-performance-engineering"
        )
        description = self.metadata["description"]
        self.assertIsInstance(description, str)
        self.assertTrue(description.strip())
        self.assertLessEqual(len(description), 600)

    def test_declared_resources_exist(self):
        self.assertTrue(self.resource_paths)
        for relative in sorted(self.resource_paths):
            with self.subTest(resource=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_published_references_are_reachable_from_entrypoint(self):
        published = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "references").glob("*.md")
        }
        self.assertTrue(published)
        self.assertFalse(published - self.resource_paths)

    def test_ui_invocation_matches_skill_identity(self):
        config = yaml.safe_load(
            (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        self.assertIn(
            "$" + self.metadata["name"], config["interface"]["default_prompt"]
        )
        self.assertIs(config["policy"]["allow_implicit_invocation"], True)


class CommandExampleRegressionTests(unittest.TestCase):
    def test_perf_c2c_forwards_record_options_after_separator(self):
        text = (ROOT / "references" / "linux-perf-workflows.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "perf c2c record -- -g -o perf-c2c.data -- ./app args", text
        )
        self.assertNotIn("perf c2c record -g", text)

    def test_default_objdump_example_is_architecture_neutral(self):
        text = (ROOT / "references" / "linux-perf-workflows.md").read_text(
            encoding="utf-8"
        )
        commands = "\n".join(re.findall(r"```bash\n(.*?)```", text, re.DOTALL))
        self.assertIn("objdump -drwC ./app", commands)
        self.assertNotIn("objdump -drwC -Mintel ./app", commands)


if __name__ == "__main__":
    unittest.main()
