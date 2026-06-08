"""Tests for skill pack marketplace."""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from autobots.marketplace import (
    BUILTIN_SKILL_PACKS,
    MARKETPLACE_URL,
    Marketplace,
    MarketplaceEntry,
    SkillPack,
    get_builtin_skill_packs,
)


class TestSkillPack(unittest.TestCase):
    """Tests for SkillPack dataclass."""

    def test_skill_pack_creation(self):
        pack = SkillPack(
            name="test-pack",
            version="1.0.0",
            author="Test Author",
            description="A test pack",
            tags=["test"],
            context_files={"architecture.md": "# Test"},
        )
        self.assertEqual(pack.name, "test-pack")
        self.assertEqual(len(pack.context_files), 1)

    def test_skill_pack_to_dict(self):
        pack = SkillPack(
            name="test",
            version="1.0.0",
            author="Author",
            description="Desc",
        )
        d = pack.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertIn("tags", d)

    def test_skill_pack_save(self):
        pack = SkillPack(
            name="test-pack",
            version="1.0.0",
            author="Author",
            description="Desc",
            context_files={"architecture.md": "# Content"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = pack.save(Path(tmpdir))
            self.assertTrue(pack_dir.exists())
            self.assertTrue((pack_dir / "skill-pack.json").exists())
            self.assertTrue((pack_dir / "context" / "architecture.md").exists())

    def test_skill_pack_create_zip(self):
        pack = SkillPack(
            name="test-pack",
            version="1.0.0",
            author="Author",
            description="Desc",
            context_files={"architecture.md": "# Content"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = pack.create_zip(Path(tmpdir))
            self.assertTrue(zip_path.exists())
            self.assertTrue(zip_path.name.endswith(".zip"))

            # Verify zip contents
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                self.assertTrue(any("skill-pack.json" in n for n in names))
                self.assertTrue(any("architecture.md" in n for n in names))


class TestMarketplaceEntry(unittest.TestCase):
    """Tests for MarketplaceEntry dataclass."""

    def test_entry_creation(self):
        entry = MarketplaceEntry(
            name="test",
            version="1.0.0",
            author="Author",
            description="Desc",
            tags=["test"],
        )
        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.downloads, 0)

    def test_entry_to_dict(self):
        entry = MarketplaceEntry(
            name="test",
            version="1.0.0",
            author="Author",
            description="Desc",
            tags=["test"],
        )
        d = entry.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertIn("downloads", d)


class TestMarketplace(unittest.TestCase):
    """Tests for Marketplace class."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry_path = Path(self.tmpdir) / "registry.json"
        self.marketplace = Marketplace(self.registry_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_empty_search(self):
        results = self.marketplace.search()
        self.assertEqual(len(results), 0)

    def test_publish_and_search(self):
        pack = SkillPack(
            name="my-pack",
            version="1.0.0",
            author="Author",
            description="My custom pack",
            tags=["custom"],
        )
        self.marketplace.publish(pack)

        results = self.marketplace.search(query="my-pack")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "my-pack")

    def test_search_by_tag(self):
        pack = SkillPack(
            name="tagged",
            version="1.0.0",
            author="Author",
            description="Desc",
            tags=["python", "web"],
        )
        self.marketplace.publish(pack)

        results = self.marketplace.search(tags=["python"])
        self.assertEqual(len(results), 1)

    def test_get_by_name(self):
        pack = SkillPack(
            name="getme",
            version="1.0.0",
            author="Author",
            description="Desc",
        )
        self.marketplace.publish(pack)

        entry = self.marketplace.get("getme")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "getme")

    def test_get_nonexistent(self):
        entry = self.marketplace.get("nonexistent")
        self.assertIsNone(entry)

    def test_registry_persistence(self):
        pack = SkillPack(
            name="persistent",
            version="1.0.0",
            author="Author",
            description="Desc",
        )
        self.marketplace.publish(pack)

        # Create new marketplace instance
        new_marketplace = Marketplace(self.registry_path)
        entry = new_marketplace.get("persistent")
        self.assertIsNotNone(entry)

    def test_install_skill_pack(self):
        pack = SkillPack(
            name="installable",
            version="1.0.0",
            author="Author",
            description="Desc",
            context_files={"architecture.md": "# Content"},
        )
        self.marketplace.publish(pack)

        target_dir = Path(self.tmpdir) / "target"
        target_dir.mkdir()

        result = self.marketplace.install("installable", target_dir)
        self.assertTrue(result)
        self.assertTrue((target_dir / "context" / "architecture.md").exists())


class TestBuiltinSkillPacks(unittest.TestCase):
    """Tests for built-in skill packs."""

    def test_builtin_packs_not_empty(self):
        packs = get_builtin_skill_packs()
        self.assertGreater(len(packs), 0)

    def test_builtin_packs_have_required_fields(self):
        packs = get_builtin_skill_packs()
        for pack in packs:
            self.assertTrue(pack.name)
            self.assertTrue(pack.version)
            self.assertTrue(pack.author)
            self.assertTrue(pack.description)
            self.assertGreater(len(pack.context_files), 0)

    def test_builtin_pack_contents(self):
        packs = get_builtin_skill_packs()
        # Check that python-web pack exists
        python_web = next((p for p in packs if p.name == "python-web"), None)
        self.assertIsNotNone(python_web)
        self.assertIn("architecture.md", python_web.context_files)


if __name__ == "__main__":
    unittest.main()
