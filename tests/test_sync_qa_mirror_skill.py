from pathlib import Path
import unittest


SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agent"
    / "skills"
    / "sync-qa-mirror"
    / "SKILL.md"
)


class SyncQaMirrorSkillTests(unittest.TestCase):
    def test_drift_check_inspects_commits_unique_to_qa_mirror(self):
        skill = SKILL_PATH.read_text()

        self.assertIn(
            "git cherry origin/<integration-branch> origin/qa-mirror",
            skill,
        )
        self.assertNotIn(
            "git cherry origin/qa-mirror origin/<integration-branch>",
            skill,
        )


if __name__ == "__main__":
    unittest.main()
