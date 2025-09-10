from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
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
from .pexels_api import PexelsApiClient, PexelsApiError
from .ddg_api import DuckDuckGoClient, DuckDuckGoError
from .yahoo_api import YahooImagesClient, YahooImagesError
from .google_cse import GoogleCSEClient
try:
	from .browser_provider import yahoo_images_playwright
	_HAS_PLAYWRIGHT = True
except Exception:
	_HAS_PLAYWRIGHT = False
from .anki_util import get_selected_note_ids, get_deck_note_ids, add_image_to_note, ensure_media_filename_safe, get_field_value


def _read_config() -> Dict[str, Any]:
	base_dir = os.path.dirname(__file__)
	config_path = os.path.join(base_dir, "config.json")
	try:
		with open(config_path, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


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
		base_dir = os.path.dirname(__file__)
		user_files_dir = os.path.join(base_dir, "user_files")
		os.makedirs(user_files_dir, exist_ok=True)
		return os.path.join(user_files_dir, "quota.json")

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

		# Field selectors
		row_q = QHBoxLayout()
		row_q.addWidget(QLabel("Query Field"))
		self.query_field = QLineEdit(self)
		self.query_field.setPlaceholderText("e.g. Expression")
		row_q.addWidget(self.query_field)
		layout.addLayout(row_q)

		row_t = QHBoxLayout()
		row_t.addWidget(QLabel("Target Field"))
		self.target_field = QLineEdit(self)
		self.target_field.setPlaceholderText("e.g. Picture")
		row_t.addWidget(self.target_field)
		layout.addLayout(row_t)

		# Suffix control
		row_suf = QHBoxLayout()
		row_suf.addWidget(QLabel("Suffix"))
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
		# Only show per-page when Pexels is enabled in provider order
		providers = self.cfg.get("provider_preference", ["ddg"]) or ["ddg"]
		if "pexels" in providers:
			row_opts.addWidget(QLabel("Per page"))
			self.per_page = QSpinBox(self)
			self.per_page.setMinimum(1)
			self.per_page.setMaximum(5)
			self.per_page.setValue(int(self.cfg.get("default_per_page", 1)))
			row_opts.addWidget(self.per_page)
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
		qconnect(self.run_btn.clicked, self._on_run)

	def _on_run(self) -> None:
		api_key = self.cfg.get("pexels_api_key", "").strip()
		provider_order = self.cfg.get("provider_preference", ["ddg", "pexels"]) or ["ddg", "pexels"]
		pexels_client = PexelsApiClient(api_key) if api_key else None
		ddg_client = DuckDuckGoClient(locale=self.cfg.get("ddg_locale", "ja-jp"))
		yahoo_client = YahooImagesClient()
		google_key = str(self.cfg.get("google_api_key", "")).strip()
		google_cx = str(self.cfg.get("google_cx", "")).strip()
		google_client = GoogleCSEClient(google_key, google_cx) if (google_key and google_cx) else None
		if "pexels" in provider_order and not api_key:
			self.logger.info("Pexels in provider_preference but API key missing; will skip Pexels.")
			provider_order = [p for p in provider_order if p != "pexels"]
		if not provider_order:
			showWarning("No providers available. Enable DDG or add a Pexels API key in config.json.")
			return

		query_field = self.query_field.text().strip()
		target_field = self.target_field.text().strip()
		replace = bool(self.replace_chk.isChecked())
		per_page = int(self.per_page.value()) if hasattr(self, "per_page") else 1

		if not query_field or not target_field:
			showWarning("Please specify both Query Field and Target Field.")
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
		media = self.mw.col.media
		used_urls: set[str] = set()
		google_used_in_run = 0
		for i, nid in enumerate(nids):
			note = col.get_note(nid)
			q = get_field_value(note, query_field)
			if not q:
				continue

			prefix = self.cfg.get("query_prefix", "")
			suffix = self.cfg.get("query_suffix", "")
			query_text = f"{prefix}{q}{suffix}".strip()
			# Suffix from UI (defaults to イラスト when left empty)
			ui_suffix = (self.suffix_field.text().strip() if hasattr(self, "suffix_field") else "") or "イラスト"
			if ui_suffix and ui_suffix not in query_text:
				query_text = f"{query_text} {ui_suffix}".strip()

			content: Optional[bytes] = None
			filename_hint: Optional[str] = None
			last_error: Optional[str] = None

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
				elif provider == "pexels" and pexels_client is not None:
					try:
						# Deterministic page selection per note id to reduce repeats
						page = max(1, (nid % 5) + 1)
						locale = self.cfg.get("pexels_locale", None)
						orientation = self.cfg.get("pexels_orientation", None)
						size = self.cfg.get("pexels_size", None)
						data = pexels_client.search_images(
							query=query_text,
							per_page=per_page,
							orientation=orientation,
							size=size,
							locale=locale,
							page=page,
						)
						photos = (data or {}).get("photos") or []
						if photos:
							photo = photos[nid % len(photos)]
							img_url = pexels_client.pick_best_src_url(photo)
							if img_url:
								content = pexels_client.download_image(img_url)
								filename_hint = ensure_media_filename_safe(f"pexels_{photo.get('id','img')}.jpg")
								break
					except Exception as e:
						last_error = f"Pexels: {e}"

			if content is None or filename_hint is None:
				if last_error:
					self.logger.error(f"All providers failed for '{q}': {last_error}")
				continue

			media_name = media.write_data(filename_hint, content)
			if add_image_to_note(note, target_field, media_name, replace=replace):
				note.flush()
				updated += 1

		col.reset()
		self.mw.reset()
		self.logger.info(f"Updated {updated} notes for field '{target_field}'")
		# Update quota display if Google was used
		if google_used_in_run:
			self._increment_google_quota(google_used_in_run)
			self.quota_label.setText(self._get_quota_display())
		showInfo(f"Updated {updated} notes.")
		self.accept()


