import unittest

from autobots.cli import _parse_plan_args


class CliPlanArgTests(unittest.TestCase):
    def test_parse_plan_args_supports_append_and_insert_after(self) -> None:
        parsed = _parse_plan_args(
            [
                "plan",
                ".",
                "--append",
                "--insert-after",
                "P2",
                "--goal",
                "Add release follow-up",
            ]
        )
        self.assertEqual(parsed, (".", "Add release follow-up", True, "P2", False))

    def test_parse_plan_args_supports_dry_run_and_legacy_goal(self) -> None:
        parsed = _parse_plan_args(["plan", ".", "--dry-run", "Prepare planning refresh"])
        self.assertEqual(parsed, (".", "Prepare planning refresh", False, None, True))


if __name__ == "__main__":
    unittest.main()
