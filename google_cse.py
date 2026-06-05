from __future__ import annotations

from typing import List, Dict, Any
import requests


class GoogleCSEError(Exception):
	pass


def _format_google_error(resp: requests.Response) -> str:
	try:
		err = (resp.json() or {}).get("error") or {}
		message = str(err.get("message") or "").strip()
		status = str(err.get("status") or "").strip()
		if message and status:
			return f"HTTP {resp.status_code} {status}: {message}"
		if message:
			return f"HTTP {resp.status_code}: {message}"
	except Exception:
		pass
	text = str(resp.text or "").strip()
	return f"HTTP {resp.status_code}: {text[:500]}"


class GoogleCSEClient:
	"""Google Custom Search JSON API wrapper (image search).

	Requires an API key and a CSE ID (cx) configured to search images on the web.
	Docs: https://developers.google.com/custom-search/v1/overview
	"""

	def __init__(self, api_key: str, cx: str) -> None:
		self._key = api_key
		self._cx = cx
		self._session = requests.Session()
		self._session.headers.update(
			{
				"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
				"Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
			}
		)

	def search_images(self, query: str, num: int = 1, start: int = 1, safe: str = "medium", lr: str | None = None) -> List[Dict[str, Any]]:
		params = {
			"key": self._key,
			"cx": self._cx,
			"q": query,
			"searchType": "image",
			"num": max(1, min(10, num)),
			"start": max(1, start),
			"safe": safe,
		}
		if lr:
			params["lr"] = lr
		resp = self._session.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=30)
		if resp.status_code != 200:
			raise GoogleCSEError(_format_google_error(resp))
		data = resp.json()
		return data.get("items", [])

	def download_image(self, url: str, timeout: float = 30.0, referer: str | None = None) -> bytes:
		headers = {}
		if referer:
			headers["Referer"] = referer
		resp = self._session.get(url, timeout=timeout, headers=headers)
		resp.raise_for_status()
		return resp.content


