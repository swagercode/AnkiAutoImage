from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.support import load_addon_module


class MediaHelperTests(unittest.TestCase):
	def setUp(self) -> None:
		self.anki_util = load_addon_module("anki_util")

	def test_ensure_media_filename_safe_strips_unsafe_characters(self) -> None:
		with patch.object(self.anki_util.time, "time", return_value=1234):
			self.assertEqual(self.anki_util.ensure_media_filename_safe("bad name あ?.jpg"), "bad_name_.jpg")
			self.assertEqual(self.anki_util.ensure_media_filename_safe("!!!"), "image_1234.jpg")

	def test_add_image_to_note_replace_and_skip_behavior(self) -> None:
		note = {"Picture": "<img src=\"old.jpg\">"}

		self.assertFalse(self.anki_util.add_image_to_note(note, "Picture", "new.jpg", replace=False))
		self.assertEqual(note["Picture"], "<img src=\"old.jpg\">")
		self.assertTrue(self.anki_util.add_image_to_note(note, "Picture", "new.jpg", replace=True))
		self.assertEqual(note["Picture"], "<img src=\"new.jpg\">")

	def test_add_audio_to_note_replace_and_missing_field_behavior(self) -> None:
		note = {"Audio": "[sound:old.mp3]"}

		self.assertFalse(self.anki_util.add_audio_to_note(note, "Missing", "new.mp3", replace=True))
		self.assertFalse(self.anki_util.add_audio_to_note(note, "Audio", "new.mp3", replace=False))
		self.assertTrue(self.anki_util.add_audio_to_note(note, "Audio", "new.mp3", replace=True))
		self.assertEqual(note["Audio"], "[sound:new.mp3]")


if __name__ == "__main__":
	unittest.main()
