from __future__ import annotations

import unittest
import sys

from tests.support import QComboBox, QKeySequence, QKeySequenceEdit, QLineEdit, QPushButton, load_addon_module


class ConfigAndSettingsTests(unittest.TestCase):
	def setUp(self) -> None:
		self.tools = load_addon_module("tools")

	def test_normalize_config_blanks_stale_placeholders_and_drops_removed_ddg_locale(self) -> None:
		cfg = self.tools._normalize_config({
			"google_api_key": "REPLACE_WITH_YOUR_GOOGLE_API_KEY",
			"google_cx": "REPLACE_WITH_YOUR_GOOGLE_CX",
			"google_genai_api_key": "REPLACE_WITH_YOUR_GENAI_API_KEY",
			"nadeshiko_api_key": "nade_real",
			"ddg_locale": "ja-jp",
			"provider_preference": ["yahoo"],
		})

		self.assertEqual(cfg["google_api_key"], "")
		self.assertEqual(cfg["google_cx"], "")
		self.assertEqual(cfg["google_genai_api_key"], "")
		self.assertEqual(cfg["nadeshiko_api_key"], "nade_real")
		self.assertNotIn("ddg_locale", cfg)

	def test_image_provider_order_allows_only_yahoo_and_configured_google_names(self) -> None:
		order = self.tools._image_provider_order({"provider_preference": ["ddg", "yahoo", "google", "yahoo", "bad"]})
		self.assertEqual(order, ["yahoo", "google"])

	def test_provider_order_widget_has_no_duckduckgo_option(self) -> None:
		widget = self.tools.ProviderOrderWidget(["yahoo", "google"])
		labels = [widget.combos[0].itemText(i) for i in range(widget.combos[0].count())]
		values = [widget.combos[0].itemData(i) for i in range(widget.combos[0].count())]

		self.assertEqual(labels, ["None", "Yahoo", "Google"])
		self.assertEqual(values, ["", "yahoo", "google"])
		self.assertEqual(widget.value(), ["yahoo", "google"])

	def test_legacy_google_tab_is_last(self) -> None:
		self.assertEqual(self.tools.SettingsDialog._TAB_ORDER[-1][0], "Legacy Google")

	def test_nadeshiko_sentence_selection_dropdown_has_expected_modes(self) -> None:
		dialog = self.tools.SettingsDialog.__new__(self.tools.SettingsDialog)
		widget = dialog._make_widget("nadeshiko_sentence_selection", "longest", "median")

		labels = [widget.itemText(i) for i in range(widget.count())]
		values = [widget.itemData(i) for i in range(widget.count())]
		self.assertEqual(labels, ["Longest (longest)", "Random (random)", "Smallest (smallest)", "Median (median)"])
		self.assertEqual(values, ["longest", "random", "smallest", "median"])
		self.assertEqual(widget.currentData(), "median")

	def test_settings_display_and_save_treat_replace_placeholders_as_blank(self) -> None:
		dialog = self.tools.SettingsDialog.__new__(self.tools.SettingsDialog)
		dialog.widgets = {"google_api_key": QLineEdit()}
		dialog.widgets["google_api_key"].setText("REPLACE_WITH_YOUR_GOOGLE_API_KEY")

		self.assertEqual(dialog._display_value("google_api_key", "", "REPLACE_WITH_YOUR_GOOGLE_API_KEY"), "")
		self.assertEqual(dialog._value_from_widget("google_api_key", ""), "")

	def test_editable_combo_placeholder_saves_blank(self) -> None:
		dialog = self.tools.SettingsDialog.__new__(self.tools.SettingsDialog)
		combo = QComboBox()
		combo.setEditable(True)
		combo.setEditText("REPLACE_WITH_VALUE")
		dialog.widgets = {"some_key": combo}

		self.assertEqual(dialog._value_from_widget("some_key", ""), "")

	def test_hotkey_settings_use_key_sequence_editor(self) -> None:
		dialog = self.tools.SettingsDialog.__new__(self.tools.SettingsDialog)
		widget = dialog._make_widget("reviewer_hotkey", "Ctrl+Shift+G", "Ctrl+Shift+G")
		dialog.widgets = {"reviewer_hotkey": widget}

		self.assertIsInstance(widget, QKeySequenceEdit)
		self.assertEqual(widget.keySequence().toString(), "Ctrl+Shift+G")
		self.assertTrue(widget.clear_button_enabled)
		self.assertEqual(widget.maximum_sequence_length, 1)

		widget.setKeySequence(QKeySequence("Alt+G"))
		self.assertEqual(dialog._value_from_widget("reviewer_hotkey", ""), "Alt+G")

		dialog._set_widget_value(widget, "Ctrl+Shift+Y")
		self.assertEqual(widget.keySequence().toString(), "Ctrl+Shift+Y")

	def test_api_key_settings_have_browser_help_buttons(self) -> None:
		dialog = self.tools.SettingsDialog.__new__(self.tools.SettingsDialog)
		expected = {
			"nadeshiko_api_key": ("Get key", "https://nadeshiko.co/user/developer"),
			"google_genai_api_key": ("Get key", "https://aistudio.google.com/apikey"),
			"google_api_key": ("Get key", "https://developers.google.com/custom-search/v1/introduction"),
			"google_cx": ("Create search engine", "https://programmablesearchengine.google.com/controlpanel/all"),
		}

		for key, (label, url) in expected.items():
			with self.subTest(key=key):
				field = QLineEdit()
				wrapped = dialog._wrap_widget_with_help(key, field)
				button = wrapped.layout.children[1]

				self.assertIs(wrapped.layout.children[0], field)
				self.assertIsInstance(button, QPushButton)
				self.assertEqual(button.text, label)
				button.clicked.emit()
				self.assertEqual(sys.modules["aqt.utils"].opened_links[-1], url)


if __name__ == "__main__":
	unittest.main()
