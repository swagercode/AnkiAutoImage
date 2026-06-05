from __future__ import annotations

import importlib.util
import sys
import unittest

from tests.support import PACKAGE, ROOT, install_anki_stubs


def load_addon_package(config: dict):
	for name in list(sys.modules):
		if name == PACKAGE or name.startswith(f"{PACKAGE}."):
			del sys.modules[name]
	mw = install_anki_stubs()
	mw.addonManager.config = dict(config)
	spec = importlib.util.spec_from_file_location(
		PACKAGE,
		ROOT / "__init__.py",
		submodule_search_locations=[str(ROOT)],
	)
	module = importlib.util.module_from_spec(spec)
	sys.modules[PACKAGE] = module
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return mw


class StartupShortcutTests(unittest.TestCase):
	def test_startup_uses_anki_managed_hotkey_settings(self) -> None:
		mw = load_addon_package({
			"reviewer_hotkey": "Alt+G",
			"reviewer_hotkey_nadeshiko": "",
			"reviewer_hotkey_genai": "Alt+U",
		})

		sequences = [shortcut.sequence.toString() for shortcut in mw._autoimage_shortcuts]
		self.assertEqual(sequences, ["Alt+G", "Alt+U"])
		self.assertEqual([shortcut.context for shortcut in mw._autoimage_shortcuts], [1, 1])


if __name__ == "__main__":
	unittest.main()
