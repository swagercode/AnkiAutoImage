from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
try:
	from zoneinfo import ZoneInfo  # Python 3.9+
	_TZ_LA = ZoneInfo("America/Los_Angeles")
except Exception:
	_TZ_LA = None

from aqt.qt import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox, QSpinBox
from aqt.qt import qconnect
from aqt import mw
from aqt.utils import showInfo, showWarning

from .logger import get_logger
from .ddg_api import DuckDuckGoClient, DuckDuckGoError
from .yahoo_api import YahooImagesClient, YahooImagesError
from .google_cse import GoogleCSEClient
try:
	from .browser_provider import yahoo_images_playwright
	_HAS_PLAYWRIGHT = True
except Exception:
	_HAS_PLAYWRIGHT = False
from .anki_util import get_selected_note_ids, get_deck_note_ids, add_image_to_note, ensure_media_filename_safe, get_field_value, add_audio_to_note
from .nadeshiko_api import NadeshikoApiClient, NadeshikoApiError
from .google_genai import GoogleGenAIClient, GoogleGenAIError


def _read_config() -> Dict[str, Any]:
	base_dir = os.path.dirname(__file__)
	config_path = os.path.join(base_dir, "config.json")
	try:
		with open(config_path, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


def _user_files_dir() -> str:
	base_dir = os.path.dirname(__file__)
	user_files_dir = os.path.join(base_dir, "user_files")
	os.makedirs(user_files_dir, exist_ok=True)
	return user_files_dir


def _last_settings_path() -> str:
	return os.path.join(_user_files_dir(), "last_settings.json")


def _read_last_settings() -> Dict[str, Any]:
	try:
		with open(_last_settings_path(), "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


def _write_last_settings(data: Dict[str, Any]) -> None:
	try:
		with open(_last_settings_path(), "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=1)
	except Exception:
		pass


class BackfillImagesDialog(QDialog):
	def __init__(self, mw, mode: str, browser=None) -> None:
		super().__init__(mw)
		self.mw = mw
		self.mode = mode  # "deck" or "browser"
		self.browser = browser
		self.logger = get_logger()
		self.cfg = _read_config()
		self.setWindowTitle("AutoImage")
		self._build_ui()

	def _quota_path(self) -> str:
		return os.path.join(_user_files_dir(), "quota.json")

	def _now_pacific(self) -> datetime:
		try:
			if _TZ_LA is not None:
				return datetime.now(_TZ_LA)
		except Exception:
			pass
		return datetime.utcnow()

	def _read_quota(self) -> Dict[str, Any]:
		try:
			with open(self._quota_path(), "r", encoding="utf-8") as f:
				return json.load(f)
		except Exception:
			return {"date": self._now_pacific().strftime("%Y-%m-%d"), "google_used": 0}

	def _write_quota(self, data: Dict[str, Any]) -> None:
		try:
			with open(self._quota_path(), "w", encoding="utf-8") as f:
				json.dump(data, f, ensure_ascii=False, indent=1)
		except Exception:
			pass

	def _get_quota_display(self) -> str:
		q = self._read_quota()
		# Reset if new Pacific day
		now = self._now_pacific()
		today = now.strftime("%Y-%m-%d")
		if q.get("date") != today:
			q = {"date": today, "google_used": 0}
			self._write_quota(q)
		used = int(q.get("google_used", 0))
		# time until Pacific midnight
		midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
		eta = midnight - now
		hrs = eta.seconds // 3600
		mins = (eta.seconds % 3600) // 60
		return f"Google quota: {used}/100, resets in {hrs:02d}:{mins:02d} (PT)"

	def _increment_google_quota(self, inc: int) -> None:
		if inc <= 0:
			return
		q = self._read_quota()
		today = self._now_pacific().strftime("%Y-%m-%d")
		if q.get("date") != today:
			q = {"date": today, "google_used": 0}
		q["google_used"] = int(q.get("google_used", 0)) + inc
		self._write_quota(q)

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)

		# Deck selector (only for deck mode)
		if self.mode == "deck":
			row = QHBoxLayout()
			row.addWidget(QLabel("Deck"))
			self.deck_combo = QComboBox(self)
			# Be compatible with multiple Anki versions
			try:
				items = list(self.mw.col.decks.all_names_and_ids())
			except Exception:
				items = []
			for item in items:
				name = getattr(item, "name", None)
				if not name and isinstance(item, (list, tuple)) and len(item) >= 1:
					name = item[0] if isinstance(item[0], str) else None
				if name:
					self.deck_combo.addItem(name)
			row.addWidget(self.deck_combo)
			layout.addLayout(row)

		# Field selectors (dropdowns populated from deck/selection)
		row_q = QHBoxLayout()
		row_q.addWidget(QLabel("Query Field"))
		self.query_field = QComboBox(self)
		row_q.addWidget(self.query_field)
		layout.addLayout(row_q)

		# Provider selector
		row_p = QHBoxLayout()
		row_p.addWidget(QLabel("Provider"))
		self.provider_combo = QComboBox(self)
		self.provider_combo.addItems(["Google", "Gemini", "Nadeshiko"])
		default_provider = str(self.cfg.get("ui_default_provider", "Google")).strip().title()
		if default_provider in ("Google", "Gemini", "Nadeshiko"):
			self.provider_combo.setCurrentText(default_provider)
		row_p.addWidget(self.provider_combo)
		layout.addLayout(row_p)

		# Target (Google/Gemini)
		row_t = QHBoxLayout()
		self.lbl_target = QLabel("Target Field")
		row_t.addWidget(self.lbl_target)
		self.target_field = QComboBox(self)
		row_t.addWidget(self.target_field)
		layout.addLayout(row_t)

		# Nadeshiko fields
		self._row_nade_img = QHBoxLayout()
		self.lbl_nade_img = QLabel("Image Field")
		self._row_nade_img.addWidget(self.lbl_nade_img)
		self.nade_image_field = QComboBox(self)
		self._row_nade_img.addWidget(self.nade_image_field)
		layout.addLayout(self._row_nade_img)

		self._row_nade_audio = QHBoxLayout()
		self.lbl_nade_audio = QLabel("Audio Field")
		self._row_nade_audio.addWidget(self.lbl_nade_audio)
		self.nade_audio_field = QComboBox(self)
		self._row_nade_audio.addWidget(self.nade_audio_field)
		layout.addLayout(self._row_nade_audio)

		self._row_nade_sentence = QHBoxLayout()
		self.lbl_nade_sentence = QLabel("Sentence Field")
		self._row_nade_sentence.addWidget(self.lbl_nade_sentence)
		self.nade_sentence_field = QComboBox(self)
		self._row_nade_sentence.addWidget(self.nade_sentence_field)
		layout.addLayout(self._row_nade_sentence)

		# Suffix control
		row_suf = QHBoxLayout()
		self.lbl_suffix = QLabel("Suffix")
		row_suf.addWidget(self.lbl_suffix)
		self.suffix_field = QLineEdit(self)
		self.suffix_field.setPlaceholderText("default イラスト")
		# Pre-fill from config if provided, else default
		prefill_suffix = str(self.cfg.get("ui_default_suffix", "イラスト")).strip()
		if prefill_suffix:
			self.suffix_field.setText(prefill_suffix)
		row_suf.addWidget(self.suffix_field)
		layout.addLayout(row_suf)

		# Options
		row_opts = QHBoxLayout()
		self.replace_chk = QCheckBox("Replace existing")
		self.replace_chk.setChecked(bool(self.cfg.get("default_replace", False)))
		row_opts.addWidget(self.replace_chk)
		layout.addLayout(row_opts)

		# Buttons
		row_btn = QHBoxLayout()
		self.run_btn = QPushButton("Run")
		self.cancel_btn = QPushButton("Cancel")
		row_btn.addWidget(self.run_btn)
		row_btn.addWidget(self.cancel_btn)
		layout.addLayout(row_btn)

		# Quota label
		self.quota_label = QLabel(self)
		self.quota_label.setText(self._get_quota_display())
		layout.addWidget(self.quota_label)

		qconnect(self.cancel_btn.clicked, self.reject)
		qconnect(self.run_btn.clicked, lambda: _on_run(self))
		# Toggle fields on provider switch
		try:
			qconnect(self.provider_combo.currentTextChanged, lambda _=None: (self._apply_last_settings_for_provider(), _toggle_provider_fields(self)))
		except Exception:
			pass

		# Populate field dropdowns initially and on deck change
		try:
			_refresh_field_dropdowns(self)
		except Exception:
			pass
		if hasattr(self, "deck_combo"):
			try:
				qconnect(self.deck_combo.currentTextChanged, lambda _=None: _refresh_field_dropdowns(self))
			except Exception:
				pass

		# Initial visibility
		self._apply_last_settings_for_provider()
		_toggle_provider_fields(self)

	def _apply_last_settings_for_provider(self) -> None:
		"""Restore last-used fields per provider when switching providers/opening UI."""
		try:
			mode = (self.provider_combo.currentText() or "").strip().lower() if hasattr(self, "provider_combo") else "google"
			last = _read_last_settings() or {}
			fields: List[str] = []
			# collect current dropdown items
			for i in range(self.query_field.count()):
				fields.append(self.query_field.itemText(i))
			def _index_of(name: str, default_idx: int = 0) -> int:
				if not name:
					return default_idx
				try:
					return fields.index(name)
				except Exception:
					return default_idx
			if mode == "google":
				lg = last.get("google", {}) if isinstance(last.get("google"), dict) else {}
				qf = str(lg.get("query_field", ""))
				tf = str(lg.get("target_field", ""))
				suf = str(lg.get("suffix", ""))
				if qf:
					self.query_field.setCurrentIndex(_index_of(qf, self.query_field.currentIndex()))
				if tf:
					self.target_field.setCurrentIndex(_index_of(tf, self.target_field.currentIndex()))
				if suf and hasattr(self, "suffix_field"):
					self.suffix_field.setText(suf)
			elif mode == "nadeshiko":
				ln = last.get("nadeshiko", {}) if isinstance(last.get("nadeshiko"), dict) else {}
				qf = str(ln.get("query_field", ""))
				imgf = str(ln.get("image_field", ""))
				audf = str(ln.get("audio_field", ""))
				sentf = str(ln.get("sentence_field", ""))
				if qf:
					self.query_field.setCurrentIndex(_index_of(qf, self.query_field.currentIndex()))
				if imgf:
					self.nade_image_field.setCurrentIndex(_index_of(imgf, self.nade_image_field.currentIndex()))
				if audf:
					self.nade_audio_field.setCurrentIndex(_index_of(audf, self.nade_audio_field.currentIndex()))
				if sentf:
					self.nade_sentence_field.setCurrentIndex(_index_of(sentf, self.nade_sentence_field.currentIndex()))
			elif mode == "gemini":
				lgm = last.get("gemini", {}) if isinstance(last.get("gemini"), dict) else {}
				qf = str(lgm.get("query_field", ""))
				tf = str(lgm.get("target_field", ""))
				if qf:
					self.query_field.setCurrentIndex(_index_of(qf, self.query_field.currentIndex()))
				if tf:
					self.target_field.setCurrentIndex(_index_of(tf, self.target_field.currentIndex()))
		except Exception:
			pass

def _strip_tags(text: str) -> str:
	try:
		return re.sub(r"<[^>]+>", "", text or "")
	except Exception:
		return text or ""

def _nade_origin(base_url: str) -> str:
	try:
		p = urlparse(base_url)
		if p.scheme and p.netloc:
			return f"{p.scheme}://{p.netloc}"
	except Exception:
		pass
	# Fallback: strip known '/api/...' suffixes
	base = str(base_url or "").strip()
	idx = base.find("/api/")
	return base[:idx] if idx != -1 else base.rstrip("/")


def _nade_normalize_url(url: str, base_url: str) -> str:
	u = str(url or "").strip()
	if not u:
		return u
	# Replace backslashes with forward slashes (API sometimes returns '\\')
	u = u.replace("\\", "/")
	if u.startswith("http://") or u.startswith("https://"):
		return u
	origin = _nade_origin(base_url)
	if u.startswith("/"):
		return f"{origin}{u}"
	return f"{origin}/{u}"


def _nadeshiko_pick_sentence(sentences: List[Dict[str, Any]], term: str) -> Optional[Dict[str, Any]]:
	"""Return the sentence item with the longest text content.

	Ignores the search term and prefers the item whose Japanese sentence
	(content_jp or content_jp_highlight stripped) is longest.
	"""
	best = None
	best_len = -1
	for it in (sentences or []):
		try:
			seg = (it or {}).get("segment_info") or {}
			jp = str(seg.get("content_jp", ""))
			hl = _strip_tags(str(seg.get("content_jp_highlight", "")))
			cand = jp if len(jp) >= len(hl) else hl
			l = len(cand)
			if l > best_len:
				best = it
				best_len = l
		except Exception:
			continue
	return best if best is not None else (sentences[0] if sentences else None)


def _collect_field_names(self, nids: List[int]) -> List[str]:
	col = self.mw.col
	seen: Dict[str, None] = {}
	for nid in (nids or [])[:1000]:
		try:
			note = col.get_note(nid)
			try:
				for name in list(note.keys()):  # type: ignore[attr-defined]
					if isinstance(name, str) and name and name not in seen:
						seen[name] = None
			except Exception:
				try:
					model = note.note_type()  # type: ignore[attr-defined]
					for fld in (model or {}).get("flds", []):
						name = fld.get("name")
						if isinstance(name, str) and name and name not in seen:
							seen[name] = None
				except Exception:
					pass
		except Exception:
			continue
	return list(seen.keys())


def _refresh_field_dropdowns(self) -> None:
	col = self.mw.col
	if self.mode == "browser" and self.browser is not None:
		nids = get_selected_note_ids(self.browser)
	else:
		deck_name = self.deck_combo.currentText() if hasattr(self, "deck_combo") else ""
		nids = get_deck_note_ids(col, deck_name)
	fields = _collect_field_names(self, nids) if nids else []
	# Reasonable defaults if empty
	if not fields:
		fields = ["Front", "Back", "Expression", "Picture"]

	def _pick_default(candidates: List[str], preferred: List[str]) -> int:
		for pref in preferred:
			if pref in candidates:
				return candidates.index(pref)
		return 0

	self.query_field.blockSignals(True)
	self.target_field.blockSignals(True)
	self.nade_image_field.blockSignals(True)
	self.nade_audio_field.blockSignals(True)
	self.nade_sentence_field.blockSignals(True)
	self.query_field.clear()
	self.target_field.clear()
	self.nade_image_field.clear()
	self.nade_audio_field.clear()
	self.nade_sentence_field.clear()
	self.query_field.addItems(fields)
	self.target_field.addItems(fields)
	self.nade_image_field.addItems(fields)
	self.nade_audio_field.addItems(fields)
	self.nade_sentence_field.addItems(fields)
	self.query_field.setCurrentIndex(_pick_default(fields, ["Expression", "Front", "Word", "Term"]))
	self.target_field.setCurrentIndex(_pick_default(fields, ["Picture", "Image", "Images", "Back"]))
	self.nade_image_field.setCurrentIndex(_pick_default(fields, ["Picture", "Image", "Images", "Back"]))
	self.nade_audio_field.setCurrentIndex(_pick_default(fields, ["Audio", "Sound", "音声"]))
	self.nade_sentence_field.setCurrentIndex(_pick_default(fields, ["Sentence", "Text", "Front", "Expression"]))
	self.query_field.blockSignals(False)
	self.target_field.blockSignals(False)
	self.nade_image_field.blockSignals(False)
	self.nade_audio_field.blockSignals(False)
	self.nade_sentence_field.blockSignals(False)

def _toggle_provider_fields(self) -> None:
	mode = (self.provider_combo.currentText() or "").strip().lower() if hasattr(self, "provider_combo") else "google"
	nade = mode == "nadeshiko"
	# Toggle visibility
	self.target_field.setVisible(not nade)
	self.lbl_target.setVisible(not nade)
	# Suffix only for Google
	show_suffix = (mode == "google")
	self.suffix_field.setVisible(show_suffix)
	self.lbl_suffix.setVisible(show_suffix)
	for lay, combo, label in [
		(self._row_nade_img, self.nade_image_field, self.lbl_nade_img),
		(self._row_nade_audio, self.nade_audio_field, self.lbl_nade_audio),
		(self._row_nade_sentence, self.nade_sentence_field, self.lbl_nade_sentence),
	]:
		try:
			combo.setVisible(nade)
			label.setVisible(nade)
		except Exception:
			pass

def _on_run(self) -> None:
	# Selected mode from UI
	provider_mode = (self.provider_combo.currentText() or "Google").strip().lower() if hasattr(self, "provider_combo") else "google"
	provider_order = self.cfg.get("provider_preference", ["ddg"]) or ["ddg"]
	ddg_client = DuckDuckGoClient(locale=self.cfg.get("ddg_locale", "ja-jp"))
	yahoo_client = YahooImagesClient()
	google_key = str(self.cfg.get("google_api_key", "")).strip()
	google_cx = str(self.cfg.get("google_cx", "")).strip()
	google_client = GoogleCSEClient(google_key, google_cx) if (google_key and google_cx) else None
	if not provider_order:
		showWarning("No providers available. Enable DDG or Google.")
		return

	query_field = (self.query_field.currentText().strip() if hasattr(self.query_field, "currentText") else str(self.query_field.text()).strip())
	target_field = (self.target_field.currentText().strip() if hasattr(self.target_field, "currentText") else str(self.target_field.text()).strip())
	replace = bool(self.replace_chk.isChecked())
	per_page = 1

	# Validate provider prerequisites up-front to avoid silent no-ops
	if provider_mode == "nadeshiko":
		key_check = str(self.cfg.get("nadeshiko_api_key", "")).strip()
		if not key_check:
			showWarning("Nadeshiko is selected, but nadeshiko_api_key is missing in config.json")
			return
	elif provider_mode == "gemini":
		genai_key_check = str(self.cfg.get("google_genai_api_key", "")).strip() or os.environ.get("GEMINI_API_KEY", "").strip()
		if not genai_key_check:
			showWarning("Gemini is selected, but google_genai_api_key is missing in config.json (or GEMINI_API_KEY env var)")
			return

	if not query_field:
		showWarning("Please specify a Query Field.")
		return
	# For non-Nadeshiko, require a generic target field
	if provider_mode != "nadeshiko" and not target_field:
		showWarning("Please specify a Target Field.")
		return

	col = self.mw.col
	if self.mode == "browser" and self.browser is not None:
		nids = get_selected_note_ids(self.browser)
		if not nids:
			showWarning("No notes selected. Please select notes in the Browser and try again.")
			return
	else:
		deck_name = self.deck_combo.currentText() if hasattr(self, "deck_combo") else ""
		nids = get_deck_note_ids(col, deck_name)
		self.logger.info(f"Searching deck: '{deck_name}' -> found {len(nids)} note ids")

	if not nids:
		showInfo("No notes found to update.")
		self.accept()
		return

	updated = 0
	empty_queries = 0
	nade_no_result = 0
	media = self.mw.col.media
	used_urls: set[str] = set()
	google_used_in_run = 0
	for i, nid in enumerate(nids):
		note = col.get_note(nid)
		q = get_field_value(note, query_field)
		if not q:
			empty_queries += 1
			continue

		note_changed = False

		prefix = self.cfg.get("query_prefix", "")
		suffix = self.cfg.get("query_suffix", "")
		query_text = f"{prefix}{q}{suffix}".strip()
		# Suffix from UI (apply only to Google image search)
		ui_suffix = (self.suffix_field.text().strip() if hasattr(self, "suffix_field") else "") or "イラスト"
		if provider_mode == "google" and ui_suffix and ui_suffix not in query_text:
			query_text = f"{query_text} {ui_suffix}".strip()

		content: Optional[bytes] = None
		filename_hint: Optional[str] = None
		last_error: Optional[str] = None

		if provider_mode == "nadeshiko":
			try:
				key = str(self.cfg.get("nadeshiko_api_key", "")).strip()
				if not key:
					continue
				base_url = str(self.cfg.get("nadeshiko_base_url", "https://api.brigadasos.xyz/api/v1")).strip() or "https://api.brigadasos.xyz/api/v1"
				client = NadeshikoApiClient(key, base_url=base_url)
				res = client.search_sentences(query=query_text, limit=1, content_sort="DESC")
				sentences = (res or {}).get("sentences") or []
				if not sentences:
					nade_no_result += 1
					continue
				it = sentences[0]
				seg = (it or {}).get("segment_info") or {}
				media_info = (it or {}).get("media_info") or {}
				img_field = (self.nade_image_field.currentText().strip() if hasattr(self, "nade_image_field") else target_field)
				aud_field = (self.nade_audio_field.currentText().strip() if hasattr(self, "nade_audio_field") else target_field)
				sent_field = (self.nade_sentence_field.currentText().strip() if hasattr(self, "nade_sentence_field") else query_field)
				lang = str(self.cfg.get("nadeshiko_sentence_lang", "jp")).lower()
				text = str(seg.get(f"content_{'en' if lang=='en' else ('es' if lang=='es' else 'jp')}") or "").strip()
				changed_sentence = False
				if sent_field in note and (replace or not note[sent_field]):
					note[sent_field] = text
					changed_sentence = True
				img_url = str(media_info.get("path_image", "")).strip()
				if img_url and img_field in note:
					img_bytes = client.download(img_url)
					tail = img_url.split("/")[-1].split("?")[0] or f"nade_{nid}.jpg"
					media_name_img = media.write_data(ensure_media_filename_safe(tail), img_bytes)
					if add_image_to_note(note, img_field, media_name_img, replace=replace):
						note_changed = True
				audio_url = str(media_info.get("path_audio", "")).strip()
				if audio_url and aud_field in note:
					aud_bytes = client.download(audio_url)
					tail = audio_url.split("/")[-1].split("?")[0] or f"nade_{nid}.mp3"
					media_name_aud = media.write_data(ensure_media_filename_safe(tail), aud_bytes)
					if add_audio_to_note(note, aud_field, media_name_aud, replace=replace):
						note_changed = True
				if changed_sentence:
					note_changed = True
				note.flush()
				if note_changed:
					updated += 1
				continue
			except Exception as e:
				last_error = f"Nadeshiko: {e}"
		elif provider_mode == "gemini":
			try:
				key = str(self.cfg.get("google_genai_api_key", "")).strip() or os.environ.get("GEMINI_API_KEY", "").strip()
				if not key:
					raise Exception("Missing google_genai_api_key or GEMINI_API_KEY")
				model = str(self.cfg.get("google_genai_model", "models/imagen-4.0-fast-generate-001"))
				aspect_ratio = str(self.cfg.get("google_genai_aspect_ratio", "1:1"))
				person_generation = str(self.cfg.get("google_genai_person_generation", "ALLOW_ALL"))
				prompt_tmpl = str(self.cfg.get("google_genai_prompt_template", "create an image to demonstrate the meaning of {term}"))
				prompt = prompt_tmpl.format(term=q)
				client = GoogleGenAIClient(key)
				imgs = client.generate_images(
					prompt=prompt,
					model=model,
					number_of_images=1,
					output_mime_type="image/jpeg",
					person_generation=person_generation,
					aspect_ratio=aspect_ratio,
				)
				if imgs:
					content = imgs[0]
					filename_hint = ensure_media_filename_safe(f"genai_{nid}.jpg")
				else:
					raise Exception("No image returned by Gemini")
			except Exception as e:
				last_error = f"GenAI: {e}"
				showWarning(f"Gemini error: {e}")
		else:
			for provider in provider_order:
				if provider == "ddg":
					try:
						items = ddg_client.search_images(query_text, max_results=50)
						if items:
							candidates = [(it.get("image") or "").strip() for it in items]
							candidates = [u for u in candidates if u]
							if not candidates:
								raise Exception("no image url")
							start = nid % len(candidates)
							pick = None
							for off in range(len(candidates)):
								cand = candidates[(start + off) % len(candidates)]
								if cand not in used_urls:
									pick = cand
									break
							if pick is None:
								pick = candidates[start]
							content = ddg_client.download_image(pick)
							# Derive filename from URL tail
							tail = pick.split("/")[-1].split("?")[0]
							if not tail or "." not in tail:
								tail = f"ddg_{nid}.jpg"
							filename_hint = ensure_media_filename_safe(tail)
							used_urls.add(pick)
							break
					except Exception as e:
						last_error = f"DDG: {e}"
				elif provider == "yahoo":
					try:
						urls = []
						if _HAS_PLAYWRIGHT and self.cfg.get("use_browser_provider", True):
							urls = yahoo_images_playwright(query_text, max_results=50)
						if not urls:
							urls = yahoo_client.search_image_urls(query_text, max_results=50)
						if urls:
							start = nid % len(urls)
							pick = None
							for off in range(len(urls)):
								cand = urls[(start + off) % len(urls)]
								if cand not in used_urls:
									pick = cand
									break
							if pick is None:
								pick = urls[start]
							content = yahoo_client.download_image(pick)
							# Derive filename from URL tail
							tail = pick.split("/")[-1].split("?")[0] or f"yahoo_{nid}.jpg"
							filename_hint = ensure_media_filename_safe(tail)
							used_urls.add(pick)
							break
					except Exception as e:
						last_error = f"Yahoo: {e}"
				elif provider == "google" and google_client is not None:
					try:
						items = google_client.search_images(query_text, num=10, lr="lang_ja")
						if items:
							candidates = [(it.get("link") or "").strip() for it in items]
							candidates = [u for u in candidates if u]
							start = nid % len(candidates)
							pick = None
							for off in range(len(candidates)):
								cand = candidates[(start + off) % len(candidates)]
								if cand not in used_urls:
									pick = cand
									break
							if pick is None:
								pick = candidates[start]
							referer = (next((it.get("image", {}) for it in items if (it.get("link") or "").strip() == pick), {}) or {}).get("contextLink")
							referer = referer or "https://www.google.com/"
							content = google_client.download_image(pick, referer=referer)
							tail = pick.split("/")[-1].split("?")[0] or f"google_{nid}.jpg"
							filename_hint = ensure_media_filename_safe(tail)
							used_urls.add(pick)
							google_used_in_run += 1
							break
					except Exception as e:
						last_error = f"Google: {e}"

		if content is None or filename_hint is None:
			if last_error:
				self.logger.error(f"All providers failed for '{q}': {last_error}")
			continue

		media_name = media.write_data(filename_hint, content)
		# For generator providers (Gemini), force replace to ensure a visible result
		replace_eff = replace if provider_mode == "google" else True
		if add_image_to_note(note, target_field, media_name, replace=replace_eff):
			note.flush()
			updated += 1

	# Save last used UI settings for reviewer hotkey
	try:
		provider_mode = (self.provider_combo.currentText() or "Google").strip().lower() if hasattr(self, "provider_combo") else "google"
		last = _read_last_settings()
		last = last or {}
		# Store per-provider
		if provider_mode == "google":
			last_google = last.get("google", {}) if isinstance(last.get("google"), dict) else {}
			last_google.update({
				"query_field": query_field,
				"target_field": target_field,
				"suffix": (self.suffix_field.text().strip() if hasattr(self, "suffix_field") else "") or "イラスト",
			})
			last["google"] = last_google
		elif provider_mode == "nadeshiko":
			last_nade = last.get("nadeshiko", {}) if isinstance(last.get("nadeshiko"), dict) else {}
			last_nade.update({
				"query_field": query_field,
				"image_field": (self.nade_image_field.currentText().strip() if hasattr(self, "nade_image_field") else ""),
				"audio_field": (self.nade_audio_field.currentText().strip() if hasattr(self, "nade_audio_field") else ""),
				"sentence_field": (self.nade_sentence_field.currentText().strip() if hasattr(self, "nade_sentence_field") else ""),
			})
			last["nadeshiko"] = last_nade
		elif provider_mode == "gemini":
			last_gem = last.get("gemini", {}) if isinstance(last.get("gemini"), dict) else {}
			last_gem.update({
				"query_field": query_field,
				"target_field": target_field,
			})
			last["gemini"] = last_gem
		_write_last_settings(last)
	except Exception:
		pass

	col.reset()
	self.mw.reset()
	self.logger.info(f"Updated {updated} notes for field '{target_field}'")
	# Update quota display if Google was used
	if google_used_in_run:
		self._increment_google_quota(google_used_in_run)
		self.quota_label.setText(self._get_quota_display())
	if provider_mode == "nadeshiko" and updated == 0:
		msg = "Updated 0 notes."
		if nade_no_result:
			msg += f" No Nadeshiko results for {nade_no_result} note(s)."
		if empty_queries:
			msg += f" Empty query field on {empty_queries} note(s)."
		showInfo(msg)
	else:
		showInfo(f"Updated {updated} notes.")
	self.accept()



# Reviewer hotkey quick-add support

def _quota_path_global() -> str:
	return os.path.join(_user_files_dir(), "quota.json")


def _increment_google_quota_global(inc: int) -> None:
	try:
		if inc <= 0:
			return
		try:
			with open(_quota_path_global(), "r", encoding="utf-8") as f:
				q = json.load(f)
		except Exception:
			q = {}
		now = datetime.now(_TZ_LA) if _TZ_LA else datetime.utcnow()
		today = now.strftime("%Y-%m-%d")
		if q.get("date") != today:
			q = {"date": today, "google_used": 0}
		q["google_used"] = int(q.get("google_used", 0)) + inc
		with open(_quota_path_global(), "w", encoding="utf-8") as f:
			json.dump(q, f, ensure_ascii=False, indent=1)
	except Exception:
		pass


def quick_add_image_for_current_card(mw) -> None:
	"""Add a Google image to the current reviewer card using last-used/default settings.

	Always overwrites the target field. Uses saved query/target/suffix if available.
	"""
	try:
		if getattr(mw, "state", "") != "review" or not getattr(getattr(mw, "reviewer", None), "card", None):
			showWarning("No active card to update.")
			return
		col = mw.col
		card = mw.reviewer.card
		note = col.get_note(card.nid)

		cfg = _read_config()
		last = _read_last_settings() or {}

		def _field_names(n) -> List[str]:
			try:
				return list(n.keys())  # type: ignore[attr-defined]
			except Exception:
				return []

		fields = _field_names(note)
		last_google = last.get("google", {}) if isinstance(last.get("google"), dict) else {}
		query_field = str(last_google.get("query_field") or last.get("query_field") or ("Expression" if "Expression" in fields else ("Front" if "Front" in fields else (fields[0] if fields else "")))).strip()
		target_field = str(last_google.get("target_field") or last.get("target_field") or ("Picture" if "Picture" in fields else ("Image" if "Image" in fields else (fields[0] if fields else "")))).strip()
		suffix_value = str(last_google.get("suffix") or last.get("suffix") or cfg.get("ui_default_suffix", "イラスト")).strip() or "イラスト"
		if not query_field or not target_field:
			showWarning("Could not determine fields to update.")
			return

		q_text = get_field_value(note, query_field).strip()
		if not q_text:
			showInfo(f"Query field '{query_field}' is empty; nothing to do.")
			return

		prefix = str(cfg.get("query_prefix", ""))
		suffix_cfg = str(cfg.get("query_suffix", ""))
		query_text = f"{prefix}{q_text}{suffix_cfg}".strip()
		if suffix_value and suffix_value not in query_text:
			query_text = f"{query_text} {suffix_value}".strip()

		key = str(cfg.get("google_api_key", "")).strip()
		cx = str(cfg.get("google_cx", "")).strip()
		if not key or not cx:
			showWarning("Google API key or CX missing in config.json")
			return

		client = GoogleCSEClient(key, cx)
		items = client.search_images(query_text, num=10, lr="lang_ja")
		if not items:
			showInfo("No images found.")
			return
		link = str(items[0].get("link") or "").strip()
		if not link:
			showInfo("No usable image link found.")
			return
		referer = items[0].get("image", {}).get("contextLink") or items[0].get("displayLink") or "https://www.google.com/"
		content = client.download_image(link, referer=referer)
		tail = link.split("/")[-1].split("?")[0] or "google.jpg"
		filename_hint = ensure_media_filename_safe(tail)
		media_name = col.media.write_data(filename_hint, content)
		if add_image_to_note(note, target_field, media_name, replace=True):
			note.flush()
			_increment_google_quota_global(1)
			col.reset()
			mw.reset()
			showInfo("Image added to current card.")
	except Exception as e:
		showWarning(f"Failed to add image: {e}")


def quick_add_nadeshiko_for_current_card(mw) -> None:
	"""Add an image and audio from Nadeshiko API to current reviewer card.

	Always overwrites the target image/audio fields. Uses saved query/target/suffix if available.
	Config keys used:
	- nadeshiko_api_key
	- nadeshiko_base_url (optional)
	- nadeshiko_image_field (fallback to last target field)
	- nadeshiko_audio_field (fallback to "Audio"/"Sound"/target field)
	- nadeshiko_query_suffix (optional; e.g., none)
	"""
	try:
		if getattr(mw, "state", "") != "review" or not getattr(getattr(mw, "reviewer", None), "card", None):
			showWarning("No active card to update.")
			return
		col = mw.col
		card = mw.reviewer.card
		note = col.get_note(card.nid)

		cfg = _read_config()
		last = _read_last_settings() or {}

		def _field_names(n) -> List[str]:
			try:
				return list(n.keys())  # type: ignore[attr-defined]
			except Exception:
				return []

		fields = _field_names(note)
		last_nade = last.get("nadeshiko", {}) if isinstance(last.get("nadeshiko"), dict) else {}
		query_field = str(last_nade.get("query_field") or ("Expression" if "Expression" in fields else ("Front" if "Front" in fields else (fields[0] if fields else "")))).strip()
		default_img_target = ("Picture" if "Picture" in fields else ("Image" if "Image" in fields else (fields[0] if fields else "")))
		image_field = str(last_nade.get("image_field") or cfg.get("nadeshiko_image_field", default_img_target)).strip() or default_img_target
		audio_field = str(last_nade.get("audio_field") or cfg.get("nadeshiko_audio_field", "")).strip()
		if not audio_field:
			for cand in ["Audio", "Sound", "音声", default_img_target]:
				if cand in fields:
					audio_field = cand
					break
		# Determine sentence field, prefer commonly used names, else fall back
		sentence_field = str(last_nade.get("sentence_field") or "").strip()
		if not sentence_field:
			for cand in ["Sentence", "Text", "Front", "Expression", query_field]:
				if cand in fields:
					sentence_field = cand
					break

		if not query_field or not image_field or not audio_field:
			showWarning("Could not determine fields to update.")
			return

		q_text = get_field_value(note, query_field).strip()
		if not q_text:
			showInfo(f"Query field '{query_field}' is empty; nothing to do.")
			return

		key = str(cfg.get("nadeshiko_api_key", "")).strip()
		if not key:
			showWarning("Missing nadeshiko_api_key in config.json")
			return
		base_url = str(cfg.get("nadeshiko_base_url", "https://api.brigadasos.xyz/api/v1")).strip() or "https://api.brigadasos.xyz/api/v1"
		client = NadeshikoApiClient(key, base_url=base_url)

		# Optional suffix
		suffix_cfg = str(cfg.get("nadeshiko_query_suffix", "")).strip()
		query_text = f"{q_text} {suffix_cfg}".strip() if suffix_cfg else q_text

		data = client.search_sentences(query=query_text, limit=1, content_sort="DESC")
		sentences = (data or {}).get("sentences") or []
		if not sentences:
			showInfo("No Nadeshiko results found.")
			return
		item = sentences[0]
		# Always write the sentence text, overwriting existing content
		updated = False
		seg = (item or {}).get("segment_info") or {}
		lang = str(cfg.get("nadeshiko_sentence_lang", "jp")).lower()
		text = str(seg.get(f"content_{'en' if lang=='en' else ('es' if lang=='es' else 'jp')}") or "").strip()
		if sentence_field and sentence_field in note:
			note[sentence_field] = text
			updated = True

		media_info = (item or {}).get("media_info") or {}
		img_url = _nade_normalize_url(media_info.get("path_image", ""), base_url)
		audio_url = _nade_normalize_url(media_info.get("path_audio", ""), base_url)

		media = col.media
		# Download and add image
		if img_url:
			img_bytes = client.download(img_url)
			img_tail = img_url.split("/")[-1].split("?")[0] or "nadeshiko.jpg"
			img_name = ensure_media_filename_safe(img_tail)
			img_media_name = media.write_data(img_name, img_bytes)
			if add_image_to_note(note, image_field, img_media_name, replace=True):
				updated = True

		# Download and add audio
		if audio_url:
			aud_bytes = client.download(audio_url)
			aud_tail = audio_url.split("/")[-1].split("?")[0] or "nadeshiko.mp3"
			aud_name = ensure_media_filename_safe(aud_tail)
			aud_media_name = media.write_data(aud_name, aud_bytes)
			if add_audio_to_note(note, audio_field, aud_media_name, replace=True):
				updated = True

		if updated:
			note.flush()
			col.reset()
			mw.reset()
			showInfo("Nadeshiko media (and sentence) added to current card.")
		else:
			showInfo("Nothing was updated.")
	except Exception as e:
		showWarning(f"Failed to add Nadeshiko media: {e}")


def quick_add_google_genai_image_for_current_card(mw) -> None:
	"""Generate an image with Google GenAI and insert into current card.

	Always overwrites the target field. Uses saved query/target/suffix if available.
	Config keys used:
	- google_genai_api_key
	- google_genai_model
	- google_genai_aspect_ratio
	- google_genai_person_generation
	- google_genai_prompt_template
	"""
	try:
		if getattr(mw, "state", "") != "review" or not getattr(getattr(mw, "reviewer", None), "card", None):
			showWarning("No active card to update.")
			return
		col = mw.col
		card = mw.reviewer.card
		note = col.get_note(card.nid)

		cfg = _read_config()
		last = _read_last_settings() or {}

		def _field_names(n) -> List[str]:
			try:
				return list(n.keys())  # type: ignore[attr-defined]
			except Exception:
				return []

		fields = _field_names(note)
		last_gem = last.get("gemini", {}) if isinstance(last.get("gemini"), dict) else {}
		query_field = str(last_gem.get("query_field") or ("Expression" if "Expression" in fields else ("Front" if "Front" in fields else (fields[0] if fields else "")))).strip()
		target_field = str(last_gem.get("target_field") or ("Picture" if "Picture" in fields else ("Image" if "Image" in fields else (fields[0] if fields else "")))).strip()
		if not query_field or not target_field:
			showWarning("Could not determine fields to update.")
			return

		q_text = get_field_value(note, query_field).strip()
		if not q_text:
			showInfo(f"Query field '{query_field}' is empty; nothing to do.")
			return

		api_key = str(cfg.get("google_genai_api_key", "")).strip() or os.environ.get("GEMINI_API_KEY", "").strip()
		if not api_key:
			showWarning("Missing google_genai_api_key in config.json")
			return
		model = str(cfg.get("google_genai_model", "models/imagen-4.0-fast-generate-001"))
		aspect_ratio = str(cfg.get("google_genai_aspect_ratio", "1:1"))
		person_generation = str(cfg.get("google_genai_person_generation", "ALLOW_ALL"))
		prompt_tmpl = str(cfg.get("google_genai_prompt_template", "create an image to demonstrate the meaning of {term}"))
		prompt = prompt_tmpl.format(term=q_text)

		client = GoogleGenAIClient(api_key)
		images = client.generate_images(
			prompt=prompt,
			model=model,
			number_of_images=1,
			output_mime_type="image/jpeg",
			person_generation=person_generation,
			aspect_ratio=aspect_ratio,
		)
		if not images:
			showInfo("No image generated.")
			return
		img_bytes = images[0]
		filename_hint = ensure_media_filename_safe("genai.jpg")
		media_name = col.media.write_data(filename_hint, img_bytes)
		if add_image_to_note(note, target_field, media_name, replace=True):
			note.flush()
			col.reset()
			mw.reset()
			showInfo("Generated image added to current card.")
		else:
			showInfo("Nothing was updated.")
	except Exception as e:
		showWarning(f"Failed to add GenAI image: {e}")
