import json
import tempfile
import unittest
from pathlib import Path

from src.main import load_config


class TestStage2(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_path = Path(self.temp_dir.name) / "config.json"

    def test_loads_valid_configuration(self):
        expected = {"vfs": "vfs.csv", "script": "scripts/stage2.sh"}
        self.config_path.write_text(json.dumps(expected), encoding="utf-8")
        self.assertEqual(load_config(str(self.config_path)), expected)

    def test_loads_null_script(self):
        self.config_path.write_text(
            '{"vfs": "vfs.csv", "script": null}', encoding="utf-8"
        )
        self.assertIsNone(load_config(str(self.config_path))["script"])

    def test_rejects_invalid_json(self):
        self.config_path.write_text("{invalid", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cannot read configuration"):
            load_config(str(self.config_path))

    def test_rejects_non_object_json(self):
        self.config_path.write_text('["vfs.csv"]', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "configuration must be a JSON object"):
            load_config(str(self.config_path))

    def test_reports_missing_config(self):
        with self.assertRaisesRegex(ValueError, "cannot read configuration"):
            load_config(str(self.config_path))


if __name__ == "__main__":
    unittest.main()
