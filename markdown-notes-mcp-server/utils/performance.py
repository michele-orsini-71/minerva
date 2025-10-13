import time
import logging
import json
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from datetime import datetime, timezone


def _get_default_logger() -> logging.Logger:
    logger = logging.getLogger('performance')
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


@contextmanager
def timer(operation_name: str, logger: Optional[logging.Logger] = None) -> Generator[Dict[str, float], None, None]:
    if logger is None:
        logger = _get_default_logger()

    timing_data = {'duration_ms': 0.0}
    start_time = time.perf_counter()

    try:
        yield timing_data
    finally:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000.0
        timing_data['duration_ms'] = duration_ms
        logger.info(f"[PERF] {operation_name}: {duration_ms:.2f}ms")


def build_perf_summary(
    operation: str,
    query_characteristics: Dict[str, Any],
    result_characteristics: Dict[str, Any],
    timing_breakdown: Dict[str, float]
) -> Dict[str, Any]:
    return {
        'operation': operation,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'query': query_characteristics,
        'results': result_characteristics,
        'timing_ms': timing_breakdown
    }


def log_perf_json(summary: Dict[str, Any], logger: Optional[logging.Logger] = None) -> None:
    if logger is None:
        logger = _get_default_logger()

    json_str = json.dumps(summary, separators=(',', ':'))
    logger.info(f"[PERF-JSON] {json_str}")
