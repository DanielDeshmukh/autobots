"""Tests for shell completions module."""

import unittest

from autobots.completions import (
    COMMANDS,
    COMPLETION_FORMATS,
    generate_bash_completion,
    generate_fish_completion,
    generate_zsh_completion,
    get_available_shells,
    get_completion_script,
)


class TestCompletionScripts(unittest.TestCase):
    """Tests for shell completion script generation."""

    def test_bash_completion_contains_complete_command(self):
        script = generate_bash_completion()
        self.assertIn("complete -F _autobots_completions autobots", script)

    def test_bash_completion_contains_commands(self):
        script = generate_bash_completion()
        for cmd in COMMANDS:
            self.assertIn(cmd, script)

    def test_zsh_completion_contains_commands(self):
        script = generate_zsh_completion()
        for cmd in COMMANDS:
            self.assertIn(cmd, script)

    def test_zsh_completion_contains_descriptions(self):
        script = generate_zsh_completion()
        self.assertIn("_describe", script)

    def test_fish_completion_contains_commands(self):
        script = generate_fish_completion()
        for cmd in COMMANDS:
            self.assertIn(cmd, script)

    def test_fish_completion_contains_complete(self):
        script = generate_fish_completion()
        self.assertIn("complete -c autobots", script)


class TestCompletionUtilities(unittest.TestCase):
    """Tests for completion utility functions."""

    def test_get_available_shells(self):
        shells = get_available_shells()
        self.assertIn("bash", shells)
        self.assertIn("zsh", shells)
        self.assertIn("fish", shells)

    def test_get_completion_script_bash(self):
        script = get_completion_script("bash")
        self.assertIsNotNone(script)
        self.assertIn("complete", script)

    def test_get_completion_script_zsh(self):
        script = get_completion_script("zsh")
        self.assertIsNotNone(script)
        self.assertIn("_arguments", script)

    def test_get_completion_script_fish(self):
        script = get_completion_script("fish")
        self.assertIsNotNone(script)
        self.assertIn("complete -c autobots", script)

    def test_get_completion_script_invalid(self):
        script = get_completion_script("invalid")
        self.assertIsNone(script)


class TestCommandList(unittest.TestCase):
    """Tests for command list."""

    def test_commands_not_empty(self):
        self.assertGreater(len(COMMANDS), 0)

    def test_commands_contain_essential(self):
        essential = ["init", "run", "engage", "doctor", "plan"]
        for cmd in essential:
            self.assertIn(cmd, COMMANDS)

    def test_completion_formats_match_shells(self):
        shells = get_available_shells()
        self.assertEqual(set(COMPLETION_FORMATS.keys()), set(shells))


if __name__ == "__main__":
    unittest.main()
