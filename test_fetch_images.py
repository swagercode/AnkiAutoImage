from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from ddg_api import DuckDuckGoClient
from yahoo_api import YahooImagesClient
from google_cse import GoogleCSEClient
try:
	from browser_provider import yahoo_images_playwright
	_HAS_PLAYWRIGHT = True
except Exception:
	_HAS_PLAYWRIGHT = False
from pexels_api import PexelsApiClient


def ensure_filename_safe(name: str) -> str:
	name = name.strip().replace(" ", "_")
	name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
	return name or "image.jpg"


def read_config(base_dir: str) -> Dict[str, Any]:
	path = os.path.join(base_dir, "config.json")
	try:
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


def save_bytes(path: str, content: bytes) -> None:
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "wb") as f:
		f.write(content)


def fetch_with_ddg(query: str, count: int, out_dir: str, cfg: Dict[str, Any]) -> int:
	client = DuckDuckGoClient(locale=str(cfg.get("ddg_locale", "ja-jp")))
	items = client.search_images(query, max_results=max(50, count * 5))
	seen_urls: set[str] = set()
	saved = 0
	for idx, item in enumerate(items):
		url = (item.get("image") or "").strip()
		if not url or url in seen_urls:
			continue
		try:
			content = client.download_image(url)
			tail = url.split("/")[-1].split("?")[0]
			if not tail or "." not in tail:
				tail = f"ddg_{idx}.jpg"
			filename = ensure_filename_safe(tail)
			path = os.path.join(out_dir, filename)
			save_bytes(path, content)
			saved += 1
			seen_urls.add(url)
			print(f"DDG: saved {path}")
			if saved >= count:
				break
		except Exception as e:
			print(f"DDG download failed: {e}")
	return saved


def fetch_with_yahoo(query: str, count: int, out_dir: str, cfg: Dict[str, Any]) -> int:
	client = YahooImagesClient()
	urls: List[str] = []
	if _HAS_PLAYWRIGHT and cfg.get("use_browser_provider", True):
		try:
			urls = yahoo_images_playwright(query, max_results=max(60, count * 10))
		except Exception as e:
			print(f"Browser provider failed: {e}")
	if not urls:
		urls = client.search_image_urls(query, max_results=max(60, count * 10))
	saved = 0
	seen: set[str] = set()
	for idx, url in enumerate(urls):
		if not url or url in seen:
			continue
		try:
			content = client.download_image(url)
			tail = url.split("/")[-1].split("?")[0] or f"yahoo_{idx}.jpg"
			filename = ensure_filename_safe(tail)
			path = os.path.join(out_dir, filename)
			save_bytes(path, content)
			saved += 1
			seen.add(url)
			print(f"Yahoo: saved {path}")
			if saved >= count:
				break
		except Exception as e:
			print(f"Yahoo download failed: {e}")
	return saved


def fetch_with_pexels(query: str, count: int, out_dir: str, cfg: Dict[str, Any]) -> int:
	api_key = str(cfg.get("pexels_api_key", "")).strip()
	if not api_key:
		print("Skipping Pexels: missing api key in config.json -> pexels_api_key")
		return 0
	client = PexelsApiClient(api_key)
	per_page = min(80, max(1, count))
	data = client.search_images(
		query=query,
		per_page=per_page,
		orientation=cfg.get("pexels_orientation"),
		size=cfg.get("pexels_size"),
		locale=cfg.get("pexels_locale"),
	)
	photos = (data or {}).get("photos") or []
	saved = 0
	for idx, photo in enumerate(photos):
		try:
			img_url = client.pick_best_src_url(photo) or ""
			if not img_url:
				continue
			content = client.download_image(img_url)
			filename = ensure_filename_safe(f"pexels_{photo.get('id','img')}.jpg")
			path = os.path.join(out_dir, filename)
			save_bytes(path, content)
			saved += 1
			print(f"Pexels: saved {path}")
			if saved >= count:
				break
		except Exception as e:
			print(f"Pexels download failed: {e}")
	return saved


def main() -> None:
	parser = argparse.ArgumentParser(description="Quick image fetch test")
	parser.add_argument("--query", required=True, help="Search query text")
	parser.add_argument("--count", type=int, default=5, help="How many images to save")
	parser.add_argument("--out", default="test_images", help="Output directory")
	parser.add_argument("--provider", default="auto", choices=["auto", "ddg", "pexels", "yahoo", "google"], help="Provider to use")
	args = parser.parse_args()

	base_dir = os.path.dirname(__file__)
	cfg = read_config(base_dir)

	prefix = cfg.get("query_prefix", "")
	suffix = cfg.get("query_suffix", "")
	force_append = str(cfg.get("force_append", "")).strip()
	query = f"{prefix}{args.query}{suffix}{(' ' + force_append) if force_append and not suffix.endswith(force_append) else ''}".strip()
	if cfg.get("append_photo_suffix", True) and not suffix and any(ord(c) >= 128 for c in args.query):
		query = f"{query} 写真".strip()

	out_dir = os.path.join(base_dir, args.out)
	os.makedirs(out_dir, exist_ok=True)

	saved = 0
	order: List[str]
	if args.provider == "auto":
		order = cfg.get("provider_preference", ["ddg", "pexels"]) or ["ddg", "pexels"]
	else:
		order = [args.provider]

	for provider in order:
		if saved >= args.count:
			break
		remaining = args.count - saved
		if provider == "ddg":
			saved += fetch_with_ddg(query, remaining, out_dir, cfg)
		elif provider == "pexels":
			saved += fetch_with_pexels(query, remaining, out_dir, cfg)
		elif provider == "yahoo":
			saved += fetch_with_yahoo(query, remaining, out_dir, cfg)
		elif provider == "google":
			key = str(cfg.get("google_api_key", "")).strip()
			cx = str(cfg.get("google_cx", "")).strip()
			if not key or not cx:
				print("Google CSE missing 'google_api_key' or 'google_cx' in config.json")
			else:
				client = GoogleCSEClient(key, cx)
				items = client.search_images(query, num=remaining, lr="lang_ja")
				for idx, it in enumerate(items):
					link = it.get("link")
					if not link:
						continue
					try:
						referer = it.get("image", {}).get("contextLink") or it.get("displayLink") or "https://www.google.com/"
						content = client.download_image(link, referer=referer)
						tail = link.split("/")[-1].split("?")[0] or f"google_{idx}.jpg"
						filename = ensure_filename_safe(tail)
						path = os.path.join(out_dir, filename)
						save_bytes(path, content)
						saved += 1
						print(f"Google: saved {path}")
						if saved >= args.count:
							break
					except Exception as e:
						print(f"Google download failed: {e}")

	print(f"Done. Saved {saved} images to {out_dir}")


if __name__ == "__main__":
	main()


