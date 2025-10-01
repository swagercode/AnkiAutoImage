from __future__ import annotations

"""
Anki add-on: Auto Images (Google)

Adds two entry points:
- Tools -> Auto Images (Google) (run over a deck)
- Browser -> Edit -> Auto Images (Google) (run over selected notes)

Configuration is read from config.json next to this file.
"""

from aqt import mw
from aqt.qt import QAction, QKeySequence, QShortcut, qconnect, Qt


def _open_tools_dialog() -> None:
	from .tools import BackfillImagesDialog
	dialog = BackfillImagesDialog(mw=mw, mode="deck", browser=None)
	dialog.exec()


def _open_browser_dialog(browser) -> None:
	from .tools import BackfillImagesDialog
	dialog = BackfillImagesDialog(mw=mw, mode="browser", browser=browser)
	dialog.exec()


def _setup_tools_menu() -> None:
	action = QAction("Auto Images (Google)", mw)
	qconnect(action.triggered, _open_tools_dialog)
	mw.form.menuTools.addAction(action)


def _setup_browser_menu_with_gui_hooks() -> bool:
	try:
		from aqt import gui_hooks

		def on_browser_menus_init(browser):
			action = QAction("Auto Images (Google)", browser)
			qconnect(action.triggered, lambda: _open_browser_dialog(browser))
			browser.form.menuEdit.addAction(action)

		def on_browser_context_menu(browser, menu):
			action = QAction("Auto Images (Google)", browser)
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
			action = QAction("Auto Images (Google)", browser)
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
			with open(cfg_path, "r", encoding="utf-8") as f:
				cfg = json.load(f)
				hotkey = str(cfg.get("reviewer_hotkey", hotkey)) or hotkey
				hotkey2 = str(cfg.get("reviewer_hotkey_nadeshiko", hotkey2)) or hotkey2
				hotkey3 = str(cfg.get("reviewer_hotkey_genai", hotkey3)) or hotkey3
		except Exception:
			pass
		sc = QShortcut(QKeySequence(hotkey), mw)
		from .tools import quick_add_image_for_current_card
		qconnect(sc.activated, lambda: quick_add_image_for_current_card(mw))
		# Second hotkey for Nadeshiko image+audio
		sc2 = QShortcut(QKeySequence(hotkey2), mw)
		from .tools import quick_add_nadeshiko_for_current_card
		qconnect(sc2.activated, lambda: quick_add_nadeshiko_for_current_card(mw))
		# Third hotkey for Google GenAI image generation
		sc3 = QShortcut(QKeySequence(hotkey3), mw)
		from .tools import quick_add_google_genai_image_for_current_card
		qconnect(sc3.activated, lambda: quick_add_google_genai_image_for_current_card(mw))
		# Ensure shortcuts are global within the app window
		try:
			sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
			sc2.setContext(Qt.ShortcutContext.ApplicationShortcut)
			sc3.setContext(Qt.ShortcutContext.ApplicationShortcut)
		except Exception:
			pass
		# Keep references to prevent garbage collection
		try:
			if not hasattr(mw, "_autoimage_shortcuts"):
				mw._autoimage_shortcuts = []
			mw._autoimage_shortcuts.extend([sc, sc2, sc3])
		except Exception:
			pass
	except Exception:
		pass


# Initialize on import
init_addon()


