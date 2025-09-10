from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

try:
	# Optional dependency for more reliable DDG access
	from duckduckgo_search import DDGS  # type: ignore
	_HAS_DDGS = True
except Exception:
	_HAS_DDGS = False


class DuckDuckGoError(Exception):
	pass


class DuckDuckGoClient:
	"""Lightweight client for DuckDuckGo image results (unofficial).

	This uses the public i.js endpoint which requires a vqd token extracted from
	the search page. No API key required.
	"""

	def __init__(self, locale: str = "ja-jp") -> None:
		self._session = requests.Session()
		self._session.headers.update(
			{
				"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
				"Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
				"Referer": "https://duckduckgo.com/",
			}
		)
		self._locale = locale
		# ddgs uses country-language format like 'jp-jp'
		self._ddgs_region = self._normalize_region_for_ddgs(locale)

	def _normalize_region_for_ddgs(self, code: str) -> str:
		c = (code or "").lower().replace("_", "-")
		if c in ("ja-jp", "jp-ja", "jp_jp", "ja_jp"):
			return "jp-jp"
		return c or "jp-jp"

	def _get_vqd(self, query: str) -> str:
		# Attempt GET with query params
		params = {"q": query, "iax": "images", "ia": "images"}
		resp = self._session.get("https://duckduckgo.com/", params=params, timeout=20)
		text = resp.text if resp.status_code == 200 else ""
		patterns = [
			r"vqd='([\w-]+)'",
			r'"vqd":"([\w-]+)"',
			r"vqd=([\w-]+)&",
			r"vqd=([\w-]+)\b",
		]
		for pat in patterns:
			m = re.search(pat, text)
			if m:
				return m.group(1)

		# Fallback: POST form
		resp2 = self._session.post("https://duckduckgo.com/", data={"q": query}, timeout=20)
		text2 = resp2.text if resp2.status_code == 200 else ""
		for pat in patterns:
			m = re.search(pat, text2)
			if m:
				return m.group(1)

		raise DuckDuckGoError("vqd token not found")

	def search_images(self, query: str, page: int = 1, max_results: int = 50) -> List[Dict[str, Any]]:
		# Prefer official library if available; it's more resilient to token changes
		if _HAS_DDGS:
			items: List[Dict[str, Any]] = []
			try:
				with DDGS() as ddgs:
					for result in ddgs.images(
						keywords=query,
						region=self._ddgs_region,
						safesearch="moderate",
						size=None,
						type_image=None,
						layout=None,
						max_results=max_results,
					):
						items.append(
							{
								"image": result.get("image"),
								"title": result.get("title"),
								"url": result.get("url"),
								"source": result.get("source"),
								"width": result.get("width"),
								"height": result.get("height"),
							}
						)
			except Exception:
				items = []
			if items:
				return items[:max_results]

		vqd = self._get_vqd(query)
		params = {
			"l": self._locale,
			"o": "json",
			"q": query,
			"vqd": vqd,
			"f": ",,,",  # filters placeholder
			"p": 1,  # safe results on
		}
		items_out: List[Dict[str, Any]] = []
		cursor_url = "https://duckduckgo.com/i.js"
		while len(items_out) < max_results:
			resp = self._session.get(cursor_url, params=params, timeout=20)
			if resp.status_code != 200:
				break
			data = resp.json()
			for item in data.get("results", []):
				try:
					items_out.append(
						{
							"image": item.get("image") or item.get("thumbnail"),
							"title": item.get("title"),
							"url": item.get("url"),
							"source": item.get("source"),
							"width": item.get("width"),
							"height": item.get("height"),
						}
					)
				except Exception:
					continue
			if not data.get("next"):  # no more pages
				break
			# Prepare next page
			cursor_url = "https://duckduckgo.com" + data["next"] if data["next"].startswith("/") else data["next"]
			params = {}  # next already encodes params
		return items_out[:max_results]

	def download_image(self, url: str, timeout: float = 30.0) -> bytes:
		resp = self._session.get(url, timeout=timeout)
		resp.raise_for_status()
		return resp.content


