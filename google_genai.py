from __future__ import annotations

import base64
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
		model: str = "gemini-3.1-flash-image",
		number_of_images: int = 1,
		output_mime_type: str = "image/png",
		person_generation: Optional[str] = None,
		aspect_ratio: str = "1:1",
	) -> List[bytes]:
		if self._is_gemini_image_model(model):
			return self._generate_gemini_images(
				prompt,
				model=model,
				output_mime_type=output_mime_type,
				aspect_ratio=aspect_ratio,
			)
		return self._generate_imagen_images(
			prompt,
			model=model,
			number_of_images=number_of_images,
			output_mime_type=output_mime_type,
			person_generation=person_generation,
			aspect_ratio=aspect_ratio,
		)

	def _is_gemini_image_model(self, model: str) -> bool:
		name = str(model or "").split("/")[-1].lower()
		return name.startswith("gemini-") and "image" in name

	def _generate_gemini_images(
		self,
		prompt: str,
		*,
		model: str,
		output_mime_type: str,
		aspect_ratio: str,
	) -> List[bytes]:
		cfg = {
			"response_modalities": ["IMAGE"],
			"response_format": {"image": {"aspect_ratio": aspect_ratio}},
		}
		try:
			result = self._client.models.generate_content(
				model=model,
				contents=[prompt],
				config=cfg,
			)
		except Exception as e:
			msg = str(e)
			if "response_format" not in msg and "responseFormat" not in msg:
				raise
			cfg.pop("response_format", None)
			result = self._client.models.generate_content(
				model=model,
				contents=[prompt],
				config=cfg,
			)

		out: List[bytes] = []
		for part in self._response_parts(result):
			inline_data = getattr(part, "inline_data", None)
			data = getattr(inline_data, "data", None)
			mime_type = str(getattr(inline_data, "mime_type", "") or "")
			if data and mime_type.startswith("image/"):
				raw = base64.b64decode(data) if isinstance(data, str) else data
				out.append(self._image_bytes_to_output(raw, output_mime_type))
				continue
			try:
				img = part.as_image()
			except Exception:
				img = None
			image_bytes = getattr(img, "image_bytes", None)
			if image_bytes:
				out.append(self._image_bytes_to_output(image_bytes, output_mime_type))
		return out

	def _response_parts(self, result: object) -> List[object]:
		parts = getattr(result, "parts", None)
		if parts:
			return list(parts)
		out: List[object] = []
		for candidate in (getattr(result, "candidates", None) or []):
			content = getattr(candidate, "content", None)
			out.extend(getattr(content, "parts", None) or [])
		return out

	def _image_bytes_to_output(self, image_bytes: bytes, output_mime_type: str) -> bytes:
		if output_mime_type.lower() != "image/jpeg":
			return image_bytes
		try:
			from PIL import Image  # type: ignore
			img = Image.open(BytesIO(image_bytes))
			if img.mode in ("RGBA", "P"):
				img = img.convert("RGB")
			buf = BytesIO()
			img.save(buf, "JPEG")
			return buf.getvalue()
		except Exception:
			return image_bytes

	def _generate_imagen_images(
		self,
		prompt: str,
		*,
		model: str,
		number_of_images: int,
		output_mime_type: str,
		person_generation: Optional[str],
		aspect_ratio: str,
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
			fmt = "JPEG" if output_mime_type.lower() == "image/jpeg" else ("PNG" if output_mime_type.lower() == "image/png" else None)
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
				tmp = tempfile.NamedTemporaryFile(delete=False, suffix=(".jpg" if fmt == "JPEG" else (".png" if fmt == "PNG" else ".img")))
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


