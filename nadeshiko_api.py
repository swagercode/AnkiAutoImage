from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests


class NadeshikoApiError(Exception):
	pass


class NadeshikoApiClient:
	"""Client for the Nadeshiko sentence/media API.

	OpenAPI summary:
	- Base URL example: https://api.brigadasos.xyz/api/v1
	- POST /search/media/sentence { query, limit, ... }
	- Response contains "sentences" list with media_info (path_image, path_audio, path_video)
	- Auth: header X-API-Key: <key>
	"""

	def __init__(self, api_key: str, base_url: str = "https://api.brigadasos.xyz/api/v1") -> None:
		if not api_key:
			raise NadeshikoApiError("Missing Nadeshiko API key")
		self._base_url = base_url.rstrip("/")
		self._session = requests.Session()
		self._session.headers.update({
			"X-API-Key": api_key,
			"Content-Type": "application/json",
			"Accept": "application/json",
		})

	def search_sentences(
		self,
		query: str,
		limit: int = 1,
		category: Optional[int] = None,
		anime_id: Optional[int] = None,
		season: Optional[List[int]] = None,
		episode: Optional[List[int]] = None,
		content_sort: Optional[str] = None,
		random_seed: Optional[float] = None,
		timeout: float = 30.0,
	) -> Dict[str, Any]:
		payload: Dict[str, Any] = {"query": query, "limit": max(1, limit)}
		if category is not None:
			payload["category"] = category
		if anime_id is not None:
			payload["anime_id"] = anime_id
		if season:
			payload["season"] = season
		if episode:
			payload["episode"] = episode
		if content_sort in ("ASC", "DESC"):
			payload["content_sort"] = content_sort
		if random_seed is not None:
			payload["random_seed"] = random_seed

		url = f"{self._base_url}/search/media/sentence"
		resp = self._session.post(url, data=json.dumps(payload), timeout=timeout)
		if resp.status_code != 200:
			raise NadeshikoApiError(f"HTTP {resp.status_code}: {resp.text}")
		data = resp.json()
		return data or {}

	def download(self, url: str, timeout: float = 60.0) -> bytes:
		resp = self._session.get(url, timeout=timeout)
		resp.raise_for_status()
		return resp.content


