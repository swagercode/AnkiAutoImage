from __future__ import annotations

"""
Anki add-on: Auto Images

Adds two entry points:
- Tools -> AutoImage -> Run (run over a deck)
- Tools -> AutoImage -> Settings (edit config)
- Browser -> Edit -> Auto Images (run over selected notes)

Configuration is read from config.json next to this file.
"""

# Ensure vendored dependencies (e.g., google-genai and its deps) are importable
try:
	import os, sys
	_base_dir = os.path.dirname(__file__)
	_vendor = os.path.join(_base_dir, "vendor")
	if os.path.isdir(_vendor) and _vendor not in sys.path:
		sys.path.insert(0, _vendor)
except Exception:
	pass

from aqt import mw
from aqt.qt import QAction, QKeySequence, QShortcut, qconnect, Qt


def _open_tools_dialog() -> None:
	from .tools import BackfillImagesDialog
	dialog = BackfillImagesDialog(mw=mw, mode="deck", browser=None)
	dialog.exec()


def _open_settings_dialog() -> None:
	from .tools import SettingsDialog
	dialog = SettingsDialog(parent=mw)
	dialog.exec()


def _open_browser_dialog(browser) -> None:
	from .tools import BackfillImagesDialog
	dialog = BackfillImagesDialog(mw=mw, mode="browser", browser=browser)
	dialog.exec()


def _setup_tools_menu() -> None:
	menu = mw.form.menuTools.addMenu("AutoImage")
	run_action = QAction("Run", mw)
	qconnect(run_action.triggered, _open_tools_dialog)
	menu.addAction(run_action)
	settings_action = QAction("Settings", mw)
	qconnect(settings_action.triggered, _open_settings_dialog)
	menu.addAction(settings_action)


def _setup_browser_menu_with_gui_hooks() -> bool:
	try:
		from aqt import gui_hooks

		def on_browser_menus_init(browser):
			action = QAction("Auto Images", browser)
			qconnect(action.triggered, lambda: _open_browser_dialog(browser))
			browser.form.menuEdit.addAction(action)

		def on_browser_context_menu(browser, menu):
			action = QAction("Auto Images", browser)
			qconnect(action.triggered, lambda: _open_browser_dialog(browser))
			menu.addSeparator()
			menu.addAction(action)

		gui_hooks.browser_menus_did_init.append(on_browser_menus_init)
		# Right-click context menu entry
		try:
			gui_hooks.browser_will_show_context_menu.append(on_browser_context_menu)
		except Exception:
			pass
		return True
	except Exception:
		return False


def _setup_browser_menu_with_legacy_hook() -> None:
	try:
		from anki.hooks import addHook

		def on_browser_setup_menus(browser):
			action = QAction("Auto Images", browser)
			qconnect(action.triggered, lambda: _open_browser_dialog(browser))
			browser.form.menuEdit.addAction(action)
			# Context menu on older Anki (fallback)
			try:
				menu = browser.form.menuEdit
				menu.addSeparator()
				menu.addAction(action)
			except Exception:
				pass

		addHook("browser.setupMenus", on_browser_setup_menus)
	except Exception:
		# Best-effort; older/newer Anki APIs may vary.
		pass


def _ensure_user_files_dir() -> None:
	import os
	base_dir = os.path.dirname(__file__)
	user_files_dir = os.path.join(base_dir, "user_files")
	try:
		os.makedirs(user_files_dir, exist_ok=True)
	except Exception:
		pass


def init_addon() -> None:
	_ensure_user_files_dir()
	_setup_tools_menu()
	try:
		mw.addonManager.setConfigAction(__name__, _open_settings_dialog)
	except Exception:
		pass
	if not _setup_browser_menu_with_gui_hooks():
		_setup_browser_menu_with_legacy_hook()
	# Reviewer hotkey (configurable via config.json -> reviewer_hotkey)
	try:
		import json, os
		base_dir = os.path.dirname(__file__)
		cfg_path = os.path.join(base_dir, "config.json")
		hotkey = "Ctrl+Shift+G"
		hotkey2 = "Ctrl+Shift+Y"
		hotkey3 = "Ctrl+Shift+U"
		try:
			# Prefer Anki-managed config from meta.json
			try:
				pkg = os.path.basename(os.path.dirname(__file__))
				cfg = mw.addonManager.getConfig(pkg) or {}
			except Exception:
				cfg = {}
			# Fallback to bundled config.json
			if not cfg:
				with open(cfg_path, "r", encoding="utf-8") as f:
					cfg = json.load(f)
			if isinstance(cfg, dict):
				if "reviewer_hotkey" in cfg:
					hotkey = str(cfg.get("reviewer_hotkey") or "").strip()
				if "reviewer_hotkey_nadeshiko" in cfg:
					hotkey2 = str(cfg.get("reviewer_hotkey_nadeshiko") or "").strip()
				if "reviewer_hotkey_genai" in cfg:
					hotkey3 = str(cfg.get("reviewer_hotkey_genai") or "").strip()
		except Exception:
			pass
		from .tools import quick_add_image_for_current_card
		from .tools import quick_add_nadeshiko_for_current_card
		from .tools import quick_add_google_genai_image_for_current_card

		def _bind_hotkey(sequence: str, callback):
			if not sequence:
				return None
			shortcut = QShortcut(QKeySequence(sequence), mw)
			qconnect(shortcut.activated, callback)
			# Ensure shortcuts are global within the app window
			try:
				shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
			except Exception:
				pass
			return shortcut

		shortcuts = [
			_bind_hotkey(hotkey, lambda: quick_add_image_for_current_card(mw)),
			_bind_hotkey(hotkey2, lambda: quick_add_nadeshiko_for_current_card(mw)),
			_bind_hotkey(hotkey3, lambda: quick_add_google_genai_image_for_current_card(mw)),
		]
		# Keep references to prevent garbage collection
		try:
			if not hasattr(mw, "_autoimage_shortcuts"):
				mw._autoimage_shortcuts = []
			mw._autoimage_shortcuts.extend(shortcut for shortcut in shortcuts if shortcut is not None)
		except Exception:
			pass
	except Exception:
		pass


# Initialize on import
init_addon()


