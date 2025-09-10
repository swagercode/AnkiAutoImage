from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests


class PexelsApiError(Exception):
	pass


class PexelsApiClient:
	"""Thin client for Pexels API.

	Docs: https://www.pexels.com/api/documentation/
	"""

	def __init__(self, api_key: str, base_url: str = "https://api.pexels.com/v1") -> None:
		self._api_key = api_key
		self._base_url = base_url.rstrip("/")
		self._session = requests.Session()
		self._session.headers.update({"Authorization": api_key})

	def search_images(
		self,
		query: str,
		per_page: int = 1,
		orientation: Optional[str] = None,
		size: Optional[str] = None,
		locale: Optional[str] = None,
		page: int = 1,
		timeout: float = 20.0,
	) -> Dict[str, Any]:
		params: Dict[str, Any] = {
			"query": query,
			"per_page": max(1, min(per_page, 80)),
			"page": max(1, page),
		}
		if orientation:
			params["orientation"] = orientation
		if size:
			params["size"] = size
		if locale:
			params["locale"] = locale

		url = f"{self._base_url}/search"
		resp = self._session.get(url, params=params, timeout=timeout)
		if resp.status_code != 200:
			raise PexelsApiError(f"Pexels API search failed: {resp.status_code} {resp.text}")
		return resp.json()

	def pick_best_src_url(self, photo: Dict[str, Any], preferred_size: str = "large") -> Optional[str]:
		src = photo.get("src") or {}
		if not isinstance(src, dict):
			return None
		# Try preferred size first, then fall back to common sizes
		candidates: List[str] = [preferred_size, "large2x", "original", "medium", "small"]
		for key in candidates:
			val = src.get(key)
			if isinstance(val, str) and val:
				return val
		return None

	def download_image(self, url: str, timeout: float = 30.0) -> bytes:
		resp = self._session.get(url, timeout=timeout)
		if resp.status_code != 200:
			raise PexelsApiError(f"Image download failed: {resp.status_code}")
		return resp.content


