from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests


class NadeshikoApiError(Exception):
	pass


class NadeshikoApiClient:
	"""Client for the Nadeshiko segment search API (v2).

	OpenAPI summary:
	- Base URL example: https://api.nadeshiko.co/v1
	- POST /search { query: {search}, take, sort, filters, ... }
	- Response contains "segments" list with urls (imageUrl, audioUrl, videoUrl)
	- Auth: header Authorization: Bearer <key>
	"""

	def __init__(self, api_key: str, base_url: str = "https://api.nadeshiko.co/v1") -> None:
		if not api_key:
			raise NadeshikoApiError("Missing Nadeshiko API key")
		self._base_url = base_url.rstrip("/")
		self._session = requests.Session()
		self._session.headers.update({
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
			"Accept": "application/json",
		})

	def search(
		self,
		query: str,
		take: int = 1,
		sort_mode: Optional[str] = None,
		min_length: Optional[int] = None,
		max_length: Optional[int] = None,
		category: Optional[List[str]] = None,
		media_include: Optional[List[str]] = None,
		timeout: float = 30.0,
	) -> Dict[str, Any]:
		payload: Dict[str, Any] = {
			"query": {"search": query},
			"take": max(1, take),
		}
		if sort_mode in ("ASC", "DESC", "NONE", "TIME_ASC", "TIME_DESC", "RANDOM"):
			payload["sort"] = {"mode": sort_mode}
		filters: Dict[str, Any] = {}
		if isinstance(min_length, int) and min_length > 0 or isinstance(max_length, int) and max_length > 0:
			length_filter: Dict[str, int] = {}
			if isinstance(min_length, int) and min_length > 0:
				length_filter["min"] = min_length
			if isinstance(max_length, int) and max_length > 0:
				length_filter["max"] = max_length
			filters["segmentLengthChars"] = length_filter
		if category:
			filters["category"] = category
		if media_include:
			filters["media"] = {"include": [{"mediaId": mid} for mid in media_include]}
		if filters:
			payload["filters"] = filters

		url = f"{self._base_url}/search"
		resp = self._session.post(url, data=json.dumps(payload), timeout=timeout)
		if resp.status_code != 200:
			raise NadeshikoApiError(f"HTTP {resp.status_code}: {resp.text}")
		data = resp.json()
		return data or {}

	def download(self, url: str, timeout: float = 60.0) -> bytes:
		resp = self._session.get(url, timeout=timeout)
		resp.raise_for_status()
		return resp.content
