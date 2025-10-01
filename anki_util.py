from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from aqt import mw
from anki.notes import Note
from anki.collection import Collection


@dataclass
class NoteTarget:
	nid: int
	note_type_name: str


def get_selected_note_ids(browser) -> List[int]:
	# Try modern attribute first
	try:
		if hasattr(browser, "selected_notes"):
			nids = browser.selected_notes()
			return list(nids)
	except Exception:
		pass
	# Legacy API
	try:
		return list(browser.selectedNotes())
	except Exception:
		pass
	# Fallback via selected cards mapping to notes
	try:
		cids = []
		if hasattr(browser, "selected_cards"):
			cids = list(browser.selected_cards())
		elif hasattr(browser, "selectedCards"):
			cids = list(browser.selectedCards())
		nids: List[int] = []
		col = mw.col  # type: ignore
		for cid in cids:
			try:
				card = col.get_card(cid)
				nids.append(card.nid)
			except Exception:
				continue
		return nids
	except Exception:
		return []


def get_deck_note_ids(col: Collection, deck_name: str) -> List[int]:
	# Include deck and its subdecks
	name = deck_name or ""
	name_escaped = name.replace('"', '\\"')
	queries: List[str] = []
	if name_escaped:
		queries.append(f"deck:\"{name_escaped}\"")
		queries.append(f"deck:\"{name_escaped}::*\"")
	else:
		# Fallback: all notes
		queries.append("")
	query = " or ".join(q for q in queries if q)
	nids = col.find_notes(query)
	return list(nids)


def ensure_media_filename_safe(name: str) -> str:
	# Keep it ASCII-ish and Anki-safe
	name = name.strip().replace(" ", "_")
	name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
	return name or f"image_{int(time.time())}.jpg"


def add_image_to_note(note: Note, field_name: str, media_filename: str, replace: bool) -> bool:
	if field_name not in note:
		return False
	img_tag = f"<img src=\"{media_filename}\">"
	cur = note[field_name]
	if cur and not replace:
		return False
	note[field_name] = img_tag if replace or not cur else (cur + "<br>" + img_tag)
	return True


def add_audio_to_note(note: Note, field_name: str, media_filename: str, replace: bool) -> bool:
	if field_name not in note:
		return False
	audio_tag = f"[sound:{media_filename}]"
	cur = note[field_name]
	if cur and not replace:
		return False
	# Preserve any existing HTML; audio tags are text
	note[field_name] = audio_tag if replace or not cur else (cur + "\n" + audio_tag)
	return True


def get_field_value(note: Note, field_name: str) -> str:
	try:
		return note[field_name]
	except Exception:
		return ""


