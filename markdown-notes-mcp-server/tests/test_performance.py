import pytest
import time
import logging
import json
from io import StringIO
from utils.performance import timer, build_perf_summary, log_perf_json


def test_timer_measures_duration():
    captured_logs = StringIO()
    handler = logging.StreamHandler(captured_logs)
    logger = logging.getLogger('test_timer')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    with timer('test_operation', logger=logger) as timing_data:
        time.sleep(0.05)

    assert timing_data['duration_ms'] >= 50.0
    assert timing_data['duration_ms'] < 100.0

    log_output = captured_logs.getvalue()
    assert '[PERF]' in log_output
    assert 'test_operation' in log_output
    assert 'ms' in log_output


def test_timer_handles_exceptions():
    captured_logs = StringIO()
    handler = logging.StreamHandler(captured_logs)
    logger = logging.getLogger('test_timer_exception')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    timing_data = None
    with pytest.raises(ValueError):
        with timer('operation_with_error', logger=logger) as timing_data:
            time.sleep(0.01)
            raise ValueError("Test error")

    assert timing_data is not None
    assert timing_data['duration_ms'] > 0

    log_output = captured_logs.getvalue()
    assert '[PERF]' in log_output
    assert 'operation_with_error' in log_output


def test_timer_with_default_logger():
    with timer('test_default_logger') as timing_data:
        time.sleep(0.01)

    assert timing_data['duration_ms'] >= 10.0


def test_build_perf_summary_structure():
    query_chars = {'length': 50, 'collection': 'test_collection'}
    result_chars = {'count': 5, 'chunks': 10}
    timing = {'total': 123.45, 'embedding': 50.0, 'search': 70.0}

    summary = build_perf_summary(
        'test_search',
        query_chars,
        result_chars,
        timing
    )

    assert summary['operation'] == 'test_search'
    assert 'timestamp' in summary
    assert summary['query'] == query_chars
    assert summary['results'] == result_chars
    assert summary['timing_ms'] == timing
    assert '2025' in summary['timestamp'] or '2024' in summary['timestamp']
    assert 'T' in summary['timestamp']


def test_log_perf_json_format():
    captured_logs = StringIO()
    handler = logging.StreamHandler(captured_logs)
    logger = logging.getLogger('test_json_log')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    summary = {
        'operation': 'test',
        'timestamp': '2025-10-13T10:00:00Z',
        'query': {'length': 10},
        'results': {'count': 5},
        'timing_ms': {'total': 100.0}
    }

    log_perf_json(summary, logger=logger)

    log_output = captured_logs.getvalue()
    assert '[PERF-JSON]' in log_output

    json_start = log_output.find('{')
    json_str = log_output[json_start:].strip()
    parsed = json.loads(json_str)

    assert parsed['operation'] == 'test'
    assert parsed['query']['length'] == 10
    assert parsed['results']['count'] == 5
    assert parsed['timing_ms']['total'] == 100.0


def test_timer_duration_precision():
    with timer('precision_test') as timing_data:
        time.sleep(0.001)

    assert timing_data['duration_ms'] >= 1.0
    assert isinstance(timing_data['duration_ms'], float)
