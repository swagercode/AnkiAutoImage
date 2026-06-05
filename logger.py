from __future__ import annotations

import logging
import os


class CloseAfterWriteRotatingHandler(logging.Handler):
	def __init__(self, path: str, max_bytes: int = 1_000_000, backup_count: int = 2) -> None:
		super().__init__()
		self.path = path
		self.max_bytes = max_bytes
		self.backup_count = backup_count

	def emit(self, record: logging.LogRecord) -> None:
		try:
			self._rotate_if_needed()
			with open(self.path, "a", encoding="utf-8") as fh:
				fh.write(self.format(record) + "\n")
		except Exception:
			self.handleError(record)

	def _rotate_if_needed(self) -> None:
		try:
			if self.max_bytes <= 0 or not os.path.exists(self.path):
				return
			if os.path.getsize(self.path) < self.max_bytes:
				return
			oldest = f"{self.path}.{self.backup_count}"
			if self.backup_count > 0 and os.path.exists(oldest):
				os.remove(oldest)
			for idx in range(self.backup_count - 1, 0, -1):
				src = f"{self.path}.{idx}"
				dst = f"{self.path}.{idx + 1}"
				if os.path.exists(src):
					os.replace(src, dst)
			if self.backup_count > 0:
				os.replace(self.path, f"{self.path}.1")
		except Exception:
			pass


def get_logger() -> logging.Logger:
	logger = logging.getLogger("anki_auto_image")
	if logger.handlers:
		return logger
	logger.setLevel(logging.INFO)
	base_dir = os.path.dirname(__file__)
	user_files_dir = os.path.join(base_dir, "user_files")
	os.makedirs(user_files_dir, exist_ok=True)
	log_path = os.path.join(user_files_dir, "auto-image.log")
	handler = CloseAfterWriteRotatingHandler(log_path, max_bytes=1_000_000, backup_count=2)
	formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	return logger


