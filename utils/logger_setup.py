"""
Centralised logging configuration for the ReWOO planner.
Usage:
    from logging_setup import logger
"""
import logging
import logging.handlers
from pathlib import Path

# 1. Ensure logs dir exists → avoids FileNotFoundError
Path("logs").mkdir(exist_ok=True)

# 2. Use RotatingFileHandler so the file never grows forever
file_handler = logging.handlers.RotatingFileHandler(
    "logs/react.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

from pythonjsonlogger.jsonlogger import JsonFormatter   # <-- new import

formatter = JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"levelname": "level", "asctime": "timestamp"},
    json_ensure_ascii=False
)

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 3. Idempotent setup: only configure once
logger = logging.getLogger("planner")
if not logger.handlers:               # ← prevents duplicates on re-import
    logger.setLevel(logging.DEBUG)    # capture everything
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# 4. Prevent propagation to root logger (avoids double lines in some setups)
logger.propagate = False