import json
import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_kv(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info(json.dumps({"msg": message, **fields}, default=str))