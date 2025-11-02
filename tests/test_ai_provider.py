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
