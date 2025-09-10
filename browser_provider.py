from __future__ import annotations

import asyncio
from typing import List


async def _search_yahoo_playwright(query: str, max_results: int = 60) -> List[str]:
	# Lazy import to avoid hard dependency when not used
	from playwright.async_api import async_playwright

	urls: List[str] = []
	async with async_playwright() as p:
		browser = await p.chromium.launch(headless=True)
		context = await browser.new_context(locale="ja-JP", user_agent=(
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
			"(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
		))
		page = await context.new_page()
		q = query
		await page.goto(f"https://search.yahoo.co.jp/image/search?p={q}&ei=UTF-8", wait_until="load")
		# Try to scroll and load more results
		for _ in range(10):
			await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
			await page.wait_for_timeout(500)
			items = await page.query_selector_all("a:has(img)")
			for a in items:
				href = await a.get_attribute("href")
				if not href:
					continue
				# Extract original image url if present
				# Typical pattern contains imgurl=<encoded>
				if "imgurl=" in href:
					from urllib.parse import unquote, parse_qs, urlparse
					qs = parse_qs(urlparse(href).query)
					u = qs.get("imgurl", [""])[0]
					if u and u not in urls:
						urls.append(unquote(u))
				if len(urls) >= max_results:
					break
			if len(urls) >= max_results:
				break
		await context.close()
		await browser.close()
	return urls[:max_results]


def yahoo_images_playwright(query: str, max_results: int = 60) -> List[str]:
	return asyncio.run(_search_yahoo_playwright(query, max_results=max_results))


