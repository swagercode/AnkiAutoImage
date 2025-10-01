from __future__ import annotations

from io import BytesIO
from typing import List, Optional
import os
import sys
import importlib


class GoogleGenAIError(Exception):
	pass


class GoogleGenAIClient:
	"""Thin wrapper around the google-genai client for image generation.

	Requires `pip install google-genai` and a valid API key.
	"""

	def __init__(self, api_key: str) -> None:
		# Try normal import first
		try:
			from google import genai  # type: ignore
		except Exception:
			# Resolve common namespace conflicts by ensuring our add-on 'google' path is on the package __path__
			base_dir = os.path.dirname(__file__)
			google_pkg_path = os.path.join(base_dir, "google")
			if os.path.isdir(google_pkg_path):
				# Prepend our path for module finding
				if base_dir not in sys.path:
					sys.path.insert(0, base_dir)
				# If a conflicting 'google' is already loaded, extend its package path
				gp = sys.modules.get("google")
				if gp is not None and hasattr(gp, "__path__"):
					try:
						gp.__path__.append(google_pkg_path)  # type: ignore[attr-defined]
					except Exception:
						pass
			try:
				genai = importlib.import_module("google.genai")  # type: ignore
			except Exception as e:
				raise GoogleGenAIError("google-genai is not installed. Run: pip install google-genai") from e
		self._genai_mod = genai
		self._client = genai.Client(api_key=api_key)

	def _ensure_installed(self) -> None:
		# Placeholder for potential runtime checks
		return

	def generate_images(
		self,
		prompt: str,
		*,
		model: str = "models/imagen-4.0-fast-generate-001",
		number_of_images: int = 1,
		output_mime_type: str = "image/jpeg",
		person_generation: Optional[str] = None,
		aspect_ratio: str = "1:1",
	) -> List[bytes]:
		# Build config dynamically; some SDK versions reject person_generation.
		cfg = dict(
			number_of_images=max(1, number_of_images),
			output_mime_type=output_mime_type,
			aspect_ratio=aspect_ratio,
		)
		if person_generation:
			cfg["person_generation"] = person_generation

		try:
			result = self._client.models.generate_images(
				model=model,
				prompt=prompt,
				config=cfg,
			)
		except Exception as e:
			msg = str(e)
			# Retry without person_generation if the SDK/model rejects it
			if "PersonGeneration" in msg or "person_generation" in msg:
				cfg.pop("person_generation", None)
				result = self._client.models.generate_images(
					model=model,
					prompt=prompt,
					config=cfg,
				)
			else:
				raise
		images = getattr(result, "generated_images", None) or []
		if not images:
			return []
		out: List[bytes] = []
		for gi in images:
			# Library surfaces PIL.Image via .image
			img = getattr(gi, "image", None)
			if img is None:
				continue
			fmt = "JPEG" if output_mime_type.lower() == "image/jpeg" else None
			# Try writing into memory first
			try:
				buf = BytesIO()
				if fmt:
					img.save(buf, fmt)
				else:
					img.save(buf)
				out.append(buf.getvalue())
			except Exception:
				# Some SDK builds only accept path-like output; use a temp file
				import tempfile
				tmp = tempfile.NamedTemporaryFile(delete=False, suffix=(".jpg" if fmt == "JPEG" else ".img"))
				try:
					tmp_path = tmp.name
					tmp.close()
					try:
						if fmt:
							img.save(tmp_path, fmt)
						else:
							img.save(tmp_path)
					except TypeError:
						img.save(tmp_path)
					with open(tmp_path, "rb") as fh:
						out.append(fh.read())
				finally:
					try:
						os.remove(tmp_path)
					except Exception:
						pass
		return out


