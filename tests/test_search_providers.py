from __future__ import annotations

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


class YahooSession:
	def __init__(self, responses) -> None:
		self.headers = {}
		self.responses = list(responses)
		self.calls = []

	def get(self, url, params=None, timeout=None):
		self.calls.append((url, params, timeout))
		return self.responses.pop(0)


class GoogleSession:
	def __init__(self, response) -> None:
		self.headers = {}
		self.response = response
		self.calls = []

	def get(self, url, params=None, timeout=None, headers=None):
		self.calls.append((url, params, timeout, headers))
		return self.response


class SearchProviderTests(unittest.TestCase):
	def test_yahoo_parser_strips_escaped_metadata_from_imgurl(self) -> None:
		yahoo = load_addon_module("yahoo_api")
		html = (
			'imgurl=https%3A%2F%2Fimg.example.com%2Fdog.jpg\\u0026refurl='
			'https%3A%2F%2Fexample.com\\u0026title=Dog"'
		)
		session = YahooSession([Response(text=html)])
		with patch.object(yahoo.requests, "Session", return_value=session):
			client = yahoo.YahooImagesClient()
			self.assertEqual(client.search_image_urls("dog"), ["https://img.example.com/dog.jpg"])

	def test_yahoo_download_returns_response_bytes(self) -> None:
		yahoo = load_addon_module("yahoo_api")
		session = YahooSession([Response(content=b"image")])
		with patch.object(yahoo.requests, "Session", return_value=session):
			client = yahoo.YahooImagesClient()
			self.assertEqual(client.download_image("https://img.example.com/dog.jpg"), b"image")

	def test_yahoo_search_falls_back_when_browser_provider_fails(self) -> None:
		tools = load_addon_module("tools")

		class Client:
			def search_image_urls(self, query, max_results=60):
				self.query = query
				self.max_results = max_results
				return ["https://img.example.com/fallback.jpg"]

		class Logger:
			def __init__(self) -> None:
				self.errors = []

			def error(self, message: str) -> None:
				self.errors.append(message)

		client = Client()
		logger = Logger()
		with patch.object(tools, "_HAS_PLAYWRIGHT", True), patch.object(
			tools, "yahoo_images_playwright", side_effect=RuntimeError("playwright missing")
		):
			urls = tools._search_yahoo_urls("dog", 5, client, use_browser_provider=True, logger=logger)

		self.assertEqual(urls, ["https://img.example.com/fallback.jpg"])
		self.assertEqual(client.query, "dog")
		self.assertEqual(client.max_results, 5)
		self.assertIn("falling back to HTTP scraper", logger.errors[0])

	def test_yahoo_proxy_filename_gets_short_image_extension(self) -> None:
		tools = load_addon_module("tools")

		self.assertEqual(
			tools._image_filename_from_url("https://msp.c.yimg.jp/images/v2/verylongproxyurl", "yahoo_123", b"\xff\xd8\xff\xe0data"),
			"yahoo_123.jpg",
		)
		self.assertEqual(
			tools._image_filename_from_url("https://img.example.com/dog.png?x=1", "yahoo_123", b"\x89PNG\r\n\x1a\ndata"),
			"dog.png",
		)

	def test_google_error_format_uses_structured_error_message(self) -> None:
		google = load_addon_module("google_cse")
		resp = Response(status_code=400, data={"error": {"status": "INVALID_ARGUMENT", "message": "API key not valid"}})

		self.assertEqual(google._format_google_error(resp), "HTTP 400 INVALID_ARGUMENT: API key not valid")

	def test_google_search_params_clamp_num_and_start(self) -> None:
		google = load_addon_module("google_cse")
		session = GoogleSession(Response(data={"items": [{"link": "https://example.com/a.jpg"}]}))
		with patch.object(google.requests, "Session", return_value=session):
			client = google.GoogleCSEClient("key", "cx")
			items = client.search_images("dog", num=99, start=-4, lr="lang_ja")

		self.assertEqual(items, [{"link": "https://example.com/a.jpg"}])
		_, params, _, _ = session.calls[0]
		self.assertEqual(params["num"], 10)
		self.assertEqual(params["start"], 1)
		self.assertEqual(params["searchType"], "image")
		self.assertEqual(params["lr"], "lang_ja")


if __name__ == "__main__":
	unittest.main()
