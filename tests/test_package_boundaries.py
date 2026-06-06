from __future__ import annotations

import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageBoundaryTests(unittest.TestCase):
	def test_build_script_does_not_package_tests_or_duckduckgo(self) -> None:
		build_script = (ROOT / "tools" / "build_addon.ps1").read_text(encoding="utf-8")

		self.assertNotIn("tests", build_script.lower())
		self.assertNotIn("ddg_api.py", build_script)

	def test_config_defaults_are_user_facing_clean(self) -> None:
		cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

		self.assertEqual(cfg["provider_preference"], ["yahoo"])
		self.assertEqual(cfg["nadeshiko_sentence_selection"], "longest")
		self.assertNotIn("ddg_locale", cfg)
		for key in ("google_api_key", "google_cx", "google_genai_api_key", "nadeshiko_api_key"):
			self.assertEqual(cfg[key], "")

	def test_readme_has_no_duckduckgo_mentions(self) -> None:
		readme = (ROOT / "README.md").read_text(encoding="utf-8")

		self.assertNotIn("DuckDuckGo", readme)

	def test_existing_archive_excludes_tests_and_duckduckgo_when_present(self) -> None:
		archive = ROOT / "AnkiAutoImage.ankiaddon"
		if not archive.exists():
			self.skipTest("AnkiAutoImage.ankiaddon has not been built")
		with zipfile.ZipFile(archive) as zf:
			names = set(zf.namelist())
			text_hits = []
			for name in names:
				if name.endswith((".py", ".json", ".md", ".ps1")):
					text = zf.read(name).decode("utf-8", errors="ignore")
					if "DuckDuckGo" in text or "ddg_api" in text:
						text_hits.append(name)

		self.assertFalse(any(name.startswith("tests/") for name in names))
		self.assertNotIn("ddg_api.py", names)
		self.assertEqual(text_hits, [])


if __name__ == "__main__":
	unittest.main()
