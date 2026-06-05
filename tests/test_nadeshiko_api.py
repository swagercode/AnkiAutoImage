from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from tests.support import load_addon_module


class Response:
	def __init__(self, status_code=200, text="", data=None, content=b"") -> None:
		self.status_code = status_code
		self.text = text
		self._data = data if data is not None else {}
		self.content = content

	def json(self):
		return self._data

	def raise_for_status(self):
		if self.status_code >= 400:
			raise RuntimeError(f"HTTP {self.status_code}")


class Session:
	def __init__(self) -> None:
		self.headers = {}
		self.posts = []

	def post(self, url, data=None, timeout=None):
		self.posts.append((url, json.loads(data), timeout))
		return Response(data={"segments": []})


class NadeshikoApiTests(unittest.TestCase):
	def setUp(self) -> None:
		self.mod = load_addon_module("nadeshiko_api")

	def test_search_uses_media_id_filter_and_length_bounds(self) -> None:
		session = Session()
		with patch.object(self.mod.requests, "Session", return_value=session):
			client = self.mod.NadeshikoApiClient("key")
			client.search("term", take=0, sort_mode="DESC", min_length=3, max_length=12, media_include=["abc"])

		url, payload, timeout = session.posts[0]
		self.assertEqual(url, "https://api.nadeshiko.co/v1/search")
		self.assertEqual(payload["take"], 1)
		self.assertEqual(payload["sort"], {"mode": "DESC"})
		self.assertEqual(payload["filters"]["segmentLengthChars"], {"min": 3, "max": 12})
		self.assertEqual(payload["filters"]["media"]["include"], [{"mediaId": "abc"}])

	def test_download_sends_auth_only_to_nadeshiko_hosts(self) -> None:
		calls = []

		def fake_get(url, headers=None, timeout=None):
			calls.append((url, headers or {}, timeout))
			return Response(content=b"ok")

		client = self.mod.NadeshikoApiClient("secret")
		with patch.object(self.mod.requests, "get", side_effect=fake_get):
			self.assertEqual(client.download("https://cdn.nadeshiko.co/media/a.webp"), b"ok")
			self.assertEqual(client.download("https://example.com/image.jpg"), b"ok")

		self.assertIn("Mozilla/5.0", calls[0][1]["User-Agent"])
		self.assertEqual(calls[0][1]["Authorization"], "Bearer secret")
		self.assertIn("Mozilla/5.0", calls[1][1]["User-Agent"])
		self.assertNotIn("Authorization", calls[1][1])


if __name__ == "__main__":
	unittest.main()
