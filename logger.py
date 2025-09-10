from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger() -> logging.Logger:
	logger = logging.getLogger("anki_auto_image")
	if logger.handlers:
		return logger
	logger.setLevel(logging.INFO)
	base_dir = os.path.dirname(__file__)
	user_files_dir = os.path.join(base_dir, "user_files")
	os.makedirs(user_files_dir, exist_ok=True)
	log_path = os.path.join(user_files_dir, "auto-image.log")
	handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
	formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	return logger


