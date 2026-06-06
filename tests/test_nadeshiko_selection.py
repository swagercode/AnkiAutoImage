from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.support import load_addon_module


def segment(text: str) -> dict:
	return {"textJa": {"content": text}}


class NadeshikoSelectionTests(unittest.TestCase):
	def setUp(self) -> None:
		self.tools = load_addon_module("tools")
		self.segments = [
			segment("aaaa"),
			segment("a"),
			segment("aaa"),
			segment("aa"),
			segment("aaaaa"),
		]

	def test_search_options_by_sentence_selection_mode(self) -> None:
		self.assertEqual(self.tools._nadeshiko_search_options({"nadeshiko_sentence_selection": "longest"}), ("longest", 1, "DESC"))
		self.assertEqual(self.tools._nadeshiko_search_options({"nadeshiko_sentence_selection": "smallest"}), ("smallest", 1, "ASC"))
		self.assertEqual(self.tools._nadeshiko_search_options({"nadeshiko_sentence_selection": "random"}), ("random", 10, "RANDOM"))
		self.assertEqual(self.tools._nadeshiko_search_options({"nadeshiko_sentence_selection": "median"}), ("median", 25, "NONE"))

	def test_sentence_selection_aliases_and_unknown_default_to_safe_modes(self) -> None:
		self.assertEqual(self.tools._nadeshiko_selection_mode({"nadeshiko_sentence_selection": "shortest"}), "smallest")
		self.assertEqual(self.tools._nadeshiko_selection_mode({"nadeshiko_sentence_selection": "middle"}), "median")
		self.assertEqual(self.tools._nadeshiko_selection_mode({"nadeshiko_sentence_selection": "bad"}), "longest")

	def test_pick_segment_by_length_modes(self) -> None:
		self.assertIs(self.tools._nadeshiko_pick_segment(self.segments, "longest"), self.segments[4])
		self.assertIs(self.tools._nadeshiko_pick_segment(self.segments, "smallest"), self.segments[1])
		self.assertIs(self.tools._nadeshiko_pick_segment(self.segments, "median"), self.segments[2])

	def test_pick_segment_random_uses_random_choice(self) -> None:
		with patch.object(self.tools.random, "choice", return_value=self.segments[3]) as choice:
			self.assertIs(self.tools._nadeshiko_pick_segment(self.segments, "random"), self.segments[3])

		choice.assert_called_once()


if __name__ == "__main__":
	unittest.main()
