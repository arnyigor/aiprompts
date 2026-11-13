import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("catalog_tool", Path(__file__).with_name("catalog.py"))
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prompts = self.root / "prompts"
        self.record = {"id": "a", "title": "Title", "category": "general", "content": {"ru": "Text"}}
        self.write(self.record)

    def write(self, record, category=None, name=None):
        path = self.prompts / (category or record["category"]) / (name or f"{record['id']}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_reproducible_complete_package(self):
        first = catalog.package(self.prompts, self.root / "first", "commit")
        second = catalog.package(self.prompts, self.root / "second", "commit")
        self.assertEqual(first, second)
        self.assertEqual((self.root / "first/prompts.zip").read_bytes(), (self.root / "second/prompts.zip").read_bytes())
        with zipfile.ZipFile(self.root / "first/prompts.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {"prompts/general/a.json", "catalog.manifest"})

    def test_duplicate_identity_and_path_mismatch(self):
        self.write(dict(self.record, category="other"))
        with self.assertRaises(ValueError):
            catalog.validate(self.prompts)

    def test_private_flags_and_empty_content_rejected(self):
        self.write(dict(self.record, is_local=True))
        with self.assertRaises(ValueError):
            catalog.validate(self.prompts)
        self.write(dict(self.record, content={"ru": " "}))
        with self.assertRaises(ValueError):
            catalog.validate(self.prompts)

    def test_stage_never_overwrites_or_publishes_personal_export(self):
        source = self.write(self.record)
        output = self.root / "review"
        catalog.stage(source, output)
        with self.assertRaises(FileExistsError):
            catalog.stage(source, output)
        self.write(dict(self.record, is_favorite=True))
        with self.assertRaises(ValueError):
            catalog.stage(source, self.root / "other")

    def test_duplicate_json_keys_rejected(self):
        self.write(self.record).write_text('{"id":"a","id":"b"}')
        with self.assertRaises(ValueError):
            catalog.validate(self.prompts)

    def test_public_candidate_removes_private_state_without_changing_source(self):
        source = self.write(dict(self.record, is_local=True, is_favorite=True, metadata={"notes": "Private"}))
        target = catalog.candidate(source, self.root / "review")
        self.assertTrue(catalog.read_json(source)["is_local"])
        public = catalog.read_json(target)
        self.assertFalse(public["is_local"])
        self.assertFalse(public["is_favorite"])
        self.assertNotIn("notes", public["metadata"])


if __name__ == "__main__":
    unittest.main()
