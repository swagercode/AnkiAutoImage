from __future__ import annotations

import re
from typing import List
from urllib.parse import unquote

import requests


class YahooImagesError(Exception):
	pass


class YahooImagesClient:
	"""Scrapes Yahoo! Japan image search result pages to extract original image URLs.

	Endpoint: https://search.yahoo.co.jp/image/search?p=<query>&ei=UTF-8
	No API key required. Best-effort scraper; subject to layout changes.
	"""

	def __init__(self, locale: str = "ja-JP") -> None:
		self._session = requests.Session()
		self._session.headers.update(
			{
				"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
				"Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
				"Referer": "https://search.yahoo.co.jp/",
			}
		)

	def search_image_urls(self, query: str, max_results: int = 60) -> List[str]:
		urls: List[str] = []
		start = 1
		while len(urls) < max_results:
			params = {"p": query, "ei": "UTF-8", "b": str(start)}
			resp = self._session.get("https://search.yahoo.co.jp/image/search", params=params, timeout=20)
			if resp.status_code != 200:
				break
			text = resp.text
			# Extract original image URLs from "imgurl=" query param in result links
			for enc in re.findall(r"imgurl=([^&\"]+)", text):
				u = unquote(enc)
				if u.startswith("http") and u not in urls:
					urls.append(u)
					if len(urls) >= max_results:
						break
			if "Next" not in text and "次へ" not in text:
				break
			start += 60
		return urls[:max_results]

	def download_image(self, url: str, timeout: float = 30.0) -> bytes:
		resp = self._session.get(url, timeout=timeout)
		resp.raise_for_status()
		return resp.content


