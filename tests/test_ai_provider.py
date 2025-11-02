import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from minerva.common.ai_config import AIProviderConfig, RateLimitConfig
from minerva.common.ai_provider import AIProvider, RateLimiter


class FakeLMStudioClient:
    def __init__(self):
        self.embeddings_calls: List[List[str]] = []
        self.chat_payloads: List[Dict[str, Any]] = []
        self.stream_payloads: List[Dict[str, Any]] = []

    def embeddings(self, model: str, texts: List[str]) -> Dict[str, Any]:
        self.embeddings_calls.append(texts)
        # Ensure deterministic output so normalization can be verified
        return {
            'data': [
                {'embedding': [1.0, 0.0, 0.0]}
            ]
        }

    def chat_completion(self, model: str, messages: List[Dict[str, Any]], temperature: float, max_tokens: Any, tools: Any, stream: bool):
        payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'tools': tools,
            'stream': stream,
        }
        if stream:
            self.stream_payloads.append(payload)
            return {
                'stream': self._stream_response()
            }

        self.chat_payloads.append(payload)
        return {
            'choices': [
                {
                    'message': {
                        'role': 'assistant',
                        'content': 'hello from lm studio'
                    },
                    'finish_reason': 'stop'
                }
            ]
        }

    def _stream_response(self):
        chunks = [
            {
                'choices': [
                    {
                        'delta': {'content': 'hello '},
                        'finish_reason': None
                    }
                ]
            },
            {
                'choices': [
                    {
                        'delta': {'content': 'world'},
                        'finish_reason': 'stop'
                    }
                ]
            }
        ]
        for chunk in chunks:
            yield chunk


def build_lmstudio_provider(rate_limit: RateLimitConfig | None = None) -> AIProvider:
    config = AIProviderConfig(
        provider_type='lmstudio',
        embedding_model='lm-embed',
        llm_model='lm-chat',
        base_url='http://localhost:1234',
        api_key=None,
        rate_limit=rate_limit
    )
    provider = AIProvider(config)
    fake_client = FakeLMStudioClient()
    provider.lmstudio_client = fake_client
    return provider


def test_generate_embedding_with_lmstudio_normalizes_vector():
    provider = build_lmstudio_provider()
    output = provider.generate_embedding('test text')
    assert pytest.approx(math.sqrt(sum(v * v for v in output)), rel=1e-6) == 1.0
    assert output[0] > output[1]


def test_chat_completion_with_lmstudio_returns_content():
    provider = build_lmstudio_provider()
    response = provider.chat_completion([
        {'role': 'user', 'content': 'say hello'}
    ])
    assert response['content'] == 'hello from lm studio'
    assert response.get('tool_calls') is None


def test_chat_completion_streaming_with_lmstudio_yields_chunks():
    provider = build_lmstudio_provider()
    stream = provider.chat_completion_streaming([
        {'role': 'user', 'content': 'say hello'}
    ])
    chunks = list(stream)
    assert len(chunks) == 2
    assert chunks[-1]['finish_reason'] == 'stop'
    assert chunks[-1]['full_content'] == 'hello world'


def test_rate_limiter_waits_when_exceeding_window(monkeypatch):
    limiter = RateLimiter(requests_per_minute=2, concurrency=None)

    sleep_calls: List[float] = []

    def fake_sleep(duration: float):
        sleep_calls.append(duration)

    limiter._sleep = fake_sleep  # type: ignore[attr-defined]

    timestamps = iter([0.0, 0.1, 0.2, 60.2])

    def fake_monotonic():
        try:
            return next(timestamps)
        except StopIteration:
            return 60.2

    monkeypatch.setattr('minerva.common.ai_provider.time.monotonic', fake_monotonic)

    with limiter:
        pass
    with limiter:
        pass
    with limiter:
        pass

    assert sleep_calls, 'RateLimiter did not pause despite exceeding rate limit'


def test_rate_limiter_concurrency_limits_parallel_requests():
    limiter = RateLimiter(requests_per_minute=None, concurrency=2)

    enter_count = 0
    max_concurrent = 0

    class Counter:
        def __init__(self):
            self.value = 0
            self.max_value = 0

        def increment(self):
            self.value += 1
            if self.value > self.max_value:
                self.max_value = self.value

        def decrement(self):
            self.value -= 1

    counter = Counter()

    with limiter:
        counter.increment()
        with limiter:
            counter.increment()
            try:
                limiter._semaphore.acquire(blocking=False)
                acquired = True
                limiter._semaphore.release()
            except:
                acquired = False
            counter.decrement()
        counter.decrement()

    assert counter.max_value <= 2


def test_rate_limiter_prunes_old_timestamps(monkeypatch):
    limiter = RateLimiter(requests_per_minute=5, concurrency=None)

    time_value = 0.0

    def fake_monotonic():
        return time_value

    monkeypatch.setattr('minerva.common.ai_provider.time.monotonic', fake_monotonic)

    with limiter:
        pass
    time_value = 1.0
    with limiter:
        pass
    time_value = 2.0
    with limiter:
        pass

    assert len(limiter._request_times) == 3

    time_value = 65.0
    with limiter:
        pass

    assert len(limiter._request_times) == 1
    assert limiter._request_times[0] == 65.0


def test_rate_limiter_from_config_returns_none_when_config_is_none():
    limiter = RateLimiter.from_config(None)
    assert limiter is None


def test_rate_limiter_from_config_creates_limiter_with_config():
    config = RateLimitConfig(requests_per_minute=10, concurrency=2)
    limiter = RateLimiter.from_config(config)
    assert limiter is not None
    assert limiter.requests_per_minute == 10
    assert limiter.concurrency == 2


def test_generate_embeddings_batch_with_lmstudio_returns_normalized_vectors():
    provider = build_lmstudio_provider()

    class BatchFakeClient:
        def embeddings(self, model: str, texts: List[str]) -> Dict[str, Any]:
            return {
                'data': [
                    {'embedding': [1.0, 0.0, 0.0]},
                    {'embedding': [0.0, 1.0, 0.0]},
                ]
            }

    provider.lmstudio_client = BatchFakeClient()
    outputs = provider.generate_embeddings_batch(['text1', 'text2'])

    assert len(outputs) == 2
    for output in outputs:
        norm = math.sqrt(sum(v * v for v in output))
        assert pytest.approx(norm, rel=1e-6) == 1.0


def test_lmstudio_provider_uses_rate_limiter_for_embeddings():
    rate_config = RateLimitConfig(requests_per_minute=10, concurrency=1)
    provider = build_lmstudio_provider(rate_limit=rate_config)

    assert provider.rate_limiter is not None
    assert provider.rate_limiter.requests_per_minute == 10
    assert provider.rate_limiter.concurrency == 1

    initial_times = len(provider.rate_limiter._request_times)
    provider.generate_embedding('test')
    assert len(provider.rate_limiter._request_times) == initial_times + 1


def test_lmstudio_provider_uses_rate_limiter_for_chat():
    rate_config = RateLimitConfig(requests_per_minute=10, concurrency=1)
    provider = build_lmstudio_provider(rate_limit=rate_config)

    assert provider.rate_limiter is not None
    assert provider.rate_limiter.requests_per_minute == 10
    assert provider.rate_limiter.concurrency == 1

    initial_times = len(provider.rate_limiter._request_times)
    provider.chat_completion([{'role': 'user', 'content': 'hello'}])
    assert len(provider.rate_limiter._request_times) == initial_times + 1


def test_lmstudio_client_raises_error_when_base_url_is_missing():
    from minerva.common.exceptions import AIProviderError
    with pytest.raises(AIProviderError, match='base_url must be provided'):
        from minerva.common.ai_provider import LMStudioClient
        LMStudioClient(base_url=None, api_key=None)


def test_lmstudio_client_adds_authorization_header_when_api_key_provided():
    from minerva.common.ai_provider import LMStudioClient
    client = LMStudioClient(base_url='http://localhost:1234', api_key='test-key')
    headers = client._headers()
    assert 'Authorization' in headers
    assert headers['Authorization'] == 'Bearer test-key'


def test_lmstudio_client_omits_authorization_header_when_no_api_key():
    from minerva.common.ai_provider import LMStudioClient
    client = LMStudioClient(base_url='http://localhost:1234', api_key=None)
    headers = client._headers()
    assert 'Authorization' not in headers


def test_chat_completion_with_tools_passes_tools_to_lmstudio():
    provider = build_lmstudio_provider()

    tools = [
        {
            'type': 'function',
            'function': {
                'name': 'search',
                'description': 'Search for information',
                'parameters': {}
            }
        }
    ]

    provider.chat_completion(
        [{'role': 'user', 'content': 'search for cats'}],
        tools=tools
    )

    fake_client = provider.lmstudio_client
    assert len(fake_client.chat_payloads) == 1
    assert fake_client.chat_payloads[0]['tools'] == tools


def test_chat_completion_with_max_tokens_passes_to_lmstudio():
    provider = build_lmstudio_provider()

    provider.chat_completion(
        [{'role': 'user', 'content': 'hello'}],
        max_tokens=100
    )

    fake_client = provider.lmstudio_client
    assert len(fake_client.chat_payloads) == 1
    assert fake_client.chat_payloads[0]['max_tokens'] == 100


def test_provider_check_availability_returns_available_when_embedding_succeeds():
    provider = build_lmstudio_provider()
    result = provider.check_availability()
    assert result['available'] is True
    assert result['dimension'] == 3
    assert result['error'] is None


def test_provider_get_embedding_metadata_includes_dimension():
    provider = build_lmstudio_provider()
    metadata = provider.get_embedding_metadata()
    assert metadata['embedding_provider'] == 'lmstudio'
    assert metadata['embedding_model'] == 'lm-embed'
    assert metadata['embedding_dimension'] == 3
