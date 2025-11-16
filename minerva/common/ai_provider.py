import json
import os
import re
import logging
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Iterable

import httpx
import litellm
import numpy as np

from minerva.common.ai_config import AIProviderConfig, APIKeyMissingError, RateLimitConfig
from minerva.common.exceptions import AIProviderError, ProviderUnavailableError


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


@contextmanager
def _suppress_litellm_debug():
    old_value = litellm.suppress_debug_info
    litellm.suppress_debug_info = True
    try:
        yield
    finally:
        litellm.suppress_debug_info = old_value


class RateLimiter:
    def __init__(self, requests_per_minute: Optional[int], concurrency: Optional[int]):
        self.requests_per_minute = requests_per_minute
        self.concurrency = concurrency
        self._lock = threading.Lock()
        self._request_times: deque[float] = deque()
        self._window = 60.0
        self._semaphore = threading.Semaphore(concurrency) if concurrency else None

    @classmethod
    def from_config(cls, config: Optional[RateLimitConfig]):
        if config is None:
            return None
        return cls(config.requests_per_minute, config.concurrency)

    def __enter__(self):
        if self._semaphore:
            self._semaphore.acquire()
        if self.requests_per_minute:
            self._acquire_token()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._semaphore:
            self._semaphore.release()

    def _acquire_token(self):
        assert self.requests_per_minute is not None
        while True:
            now = time.monotonic()
            with self._lock:
                self._prune(now)
                if len(self._request_times) < self.requests_per_minute:
                    self._request_times.append(now)
                    return
                earliest = self._request_times[0]
                wait_time = self._window - (now - earliest)
            if wait_time > 0:
                self._sleep(min(wait_time, 1.0))
            else:
                self._sleep(0.01)

    def _prune(self, now: float) -> None:
        while self._request_times and now - self._request_times[0] >= self._window:
            self._request_times.popleft()

    def _sleep(self, duration: float) -> None:
        if duration > 0:
            time.sleep(duration)


class LMStudioClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def embeddings(self, model: str, texts: List[str]) -> Dict[str, Any]:
        payload = {
            'model': model,
            'input': texts
        }
        return self._request('POST', '/v1/embeddings', json=payload)

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[List[Dict[str, Any]]],
        stream: bool
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'stream': stream
        }

        if max_tokens is not None:
            payload['max_tokens'] = max_tokens

        if tools:
            payload['tools'] = tools

        if stream:
            return {'stream': self._stream_request('/v1/chat/completions', payload)}

        return self._request('POST', '/v1/chat/completions', json=payload)

    def _headers(self) -> Dict[str, str]:
        return {'Content-Type': 'application/json'}

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop('headers', None) or self._headers()

        timeout = kwargs.pop('timeout', 60.0)

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as error:
            raise ProviderUnavailableError(f"LM Studio unreachable: {error}") from error

        try:
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise AIProviderError(f"LM Studio request failed: {error}") from error

        try:
            return response.json()
        except json.JSONDecodeError as error:
            raise AIProviderError(f"Invalid JSON response from LM Studio: {error}") from error

    def _stream_request(self, path: str, payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        headers = self._headers()

        def stream_generator():
            try:
                stream_ctx = httpx.stream('POST', url, headers=headers, json=payload, timeout=None)
            except httpx.RequestError as error:
                raise ProviderUnavailableError(f"LM Studio unreachable: {error}") from error

            with stream_ctx as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    raise AIProviderError(f"LM Studio streaming request failed: {error}") from error

                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith('data: '):
                        data = line[len('data: '):].strip()
                    else:
                        data = line.strip()

                    if not data:
                        continue

                    if data == '[DONE]':
                        break

                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

        return stream_generator()
class AIProvider:
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.api_key = config.resolve_api_key()
        self.provider_type = config.provider_type
        self.embedding_model = config.embedding_model
        self.llm_model = config.llm_model
        self.base_url = config.base_url
        self.rate_limiter = RateLimiter.from_config(config.rate_limit)
        self.using_lmstudio = self.provider_type == 'lmstudio'
        self.lmstudio_client = None

        if self.using_lmstudio:
            self.lmstudio_client = LMStudioClient(self.base_url)
        else:
            self.litellm = litellm
            self._configure_litellm()

    @contextmanager
    def _rate_limit_guard(self):
        if not self.rate_limiter:
            yield
            return
        with self.rate_limiter:
            yield

    def _configure_litellm(self):
        if self.using_lmstudio or not self.litellm:
            return

        if self.api_key:
            if self.provider_type == 'openai':
                os.environ['OPENAI_API_KEY'] = self.api_key
            elif self.provider_type == 'gemini':
                os.environ['GEMINI_API_KEY'] = self.api_key
            elif self.provider_type == 'azure':
                os.environ['AZURE_API_KEY'] = self.api_key
            elif self.provider_type == 'anthropic':
                os.environ['ANTHROPIC_API_KEY'] = self.api_key

        if self.base_url:
            if self.provider_type == 'ollama':
                os.environ['OLLAMA_API_BASE'] = self.base_url
            elif self.provider_type == 'openai':
                os.environ['OPENAI_API_BASE'] = self.base_url

        # Suppress verbose LiteLLM logging
        # LiteLLM logs every API call at INFO level, which clutters the console
        logging.getLogger('LiteLLM').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)

    def _get_model_name_for_litellm(self, model: str, for_embedding: bool = False) -> str:
        if self.provider_type == 'ollama':
            return f"ollama/{model}"
        elif self.provider_type == 'openai':
            return f"openai/{model}" if for_embedding else model
        elif self.provider_type == 'gemini':
            return f"gemini/{model}"
        elif self.provider_type == 'azure':
            return f"azure/{model}"
        elif self.provider_type == 'anthropic':
            return f"anthropic/{model}"
        else:
            return model

    def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError(
                "Cannot generate embedding for empty text\n"
                "  Received: empty or whitespace-only string\n"
                "  Suggestion: Filter out empty chunks before embedding generation"
            )

        try:
            with self._rate_limit_guard():
                if self.using_lmstudio and self.lmstudio_client:
                    response = self.lmstudio_client.embeddings(self.embedding_model, [text])
                else:
                    model_name = self._get_model_name_for_litellm(self.embedding_model, for_embedding=True)
                    response = self.litellm.embedding(
                        model=model_name,
                        input=[text]
                    )

            if not response:
                raise AIProviderError("Invalid response from provider: empty response")

            data = self._extract_embedding_data(response)

            if not data:
                raise AIProviderError("Invalid response from provider: empty embedding data")

            embedding_data = data[0]

            try:
                embedding = embedding_data.embedding
            except (AttributeError, TypeError):
                try:
                    embedding = embedding_data['embedding']  # type: ignore[index]
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from provider: missing 'embedding' field")

            if not embedding:
                raise AIProviderError("Invalid response from provider: empty embedding")

            # Convert to numpy array and normalize
            vector = np.array(embedding, dtype=np.float32)

            if vector.size == 0:
                raise AIProviderError("Received empty embedding vector")

            # L2 normalize for cosine similarity
            normalized = l2_normalize(vector.reshape(1, -1))
            return normalized.flatten().tolist()

        except (AIProviderError, ProviderUnavailableError):
            # Re-raise our own exceptions unchanged
            raise
        except Exception as error:
            # Check for connection/availability errors
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in ['connection', 'refused', 'unavailable', 'timeout']):
                raise ProviderUnavailableError(
                    f"{self.provider_type} provider is unavailable: {error}\n"
                    f"  Check that the service is running and accessible"
                ) from error
            else:
                raise AIProviderError(f"Failed to generate embedding: {error}") from error

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(
                    f"Cannot generate embedding for empty text at index {i}\n"
                    f"  Received: empty or whitespace-only string\n"
                    f"  Suggestion: Filter out empty texts before calling generate_embeddings_batch"
                )

        try:
            with self._rate_limit_guard():
                if self.using_lmstudio and self.lmstudio_client:
                    response = self.lmstudio_client.embeddings(self.embedding_model, texts)
                else:
                    model_name = self._get_model_name_for_litellm(self.embedding_model, for_embedding=True)
                    response = self.litellm.embedding(
                        model=model_name,
                        input=texts
                    )

            if not response:
                raise AIProviderError("Invalid response from provider: empty response")

            data = self._extract_embedding_data(response)

            if not data:
                raise AIProviderError("Invalid response from provider: empty embedding data")

            if len(data) != len(texts):
                raise AIProviderError(
                    f"Embedding count mismatch: expected {len(texts)}, got {len(data)}"
                )

            embeddings = []
            for embedding_data in data:
                try:
                    embedding = embedding_data.embedding
                except (AttributeError, TypeError):
                    try:
                        embedding = embedding_data['embedding']  # type: ignore[index]
                    except (KeyError, TypeError):
                        raise AIProviderError("Invalid response from provider: missing 'embedding' field")

                if not embedding:
                    raise AIProviderError("Invalid response from provider: empty embedding")

                vector = np.array(embedding, dtype=np.float32)

                if vector.size == 0:
                    raise AIProviderError("Received empty embedding vector")

                embeddings.append(vector)

            # Batch normalize all embeddings
            embeddings_array = np.array(embeddings)
            normalized = l2_normalize(embeddings_array)

            # Convert to list of lists and return
            return normalized.tolist()

        except (AIProviderError, ProviderUnavailableError):
            # Re-raise our own exceptions unchanged
            raise
        except Exception as error:
            # Check for connection/availability errors
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in ['connection', 'refused', 'unavailable', 'timeout']):
                raise ProviderUnavailableError(
                    f"{self.provider_type} provider is unavailable: {error}\n"
                    f"  Check that the service is running and accessible"
                ) from error
            else:
                raise AIProviderError(f"Failed to generate embeddings batch: {error}") from error

    def _extract_embedding_data(self, response) -> List[Any]:
        if isinstance(response, dict):
            data = response.get('data')
        else:
            try:
                data = response.data
            except (AttributeError, TypeError):
                data = None
            if data is None:
                try:
                    data = response['data']  # type: ignore[index]
                except (KeyError, TypeError):
                    data = None

        if not data:
            raise AIProviderError("Invalid response from provider: missing embedding data")

        return data

    def _chat_completion_request(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[List[Dict[str, Any]]],
        stream: bool
    ):
        with self._rate_limit_guard():
            if self.using_lmstudio and self.lmstudio_client:
                return self.lmstudio_client.chat_completion(
                    model=self.llm_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    stream=stream
                )

            if not self.litellm:
                raise AIProviderError("LiteLLM is not configured")

            model_name = self._get_model_name_for_litellm(self.llm_model, for_embedding=False)

            completion_params = {
                'model': model_name,
                'messages': messages,
                'temperature': temperature,
                'stream': stream
            }

            if max_tokens is not None:
                completion_params['max_tokens'] = max_tokens

            if tools:
                completion_params['tools'] = tools

            return self.litellm.completion(**completion_params)

    def get_embedding_metadata(self) -> Dict[str, Any]:
        metadata = {
            'embedding_provider': self.provider_type,
            'embedding_model': self.embedding_model,
            'llm_model': self.llm_model,
            'embedding_base_url': self.base_url,
            'embedding_api_key_ref': self.config.api_key,  # Return template, not resolved key!
        }

        # Try to determine embedding dimension by generating a test embedding
        # This is optional and won't fail if it doesn't work
        try:
            test_embedding = self.generate_embedding("test")
            metadata['embedding_dimension'] = len(test_embedding)
        except Exception:
            # If we can't generate a test embedding, dimension is unknown
            metadata['embedding_dimension'] = None

        return metadata

    def check_availability(self) -> Dict[str, Any]:
        result = {
            'available': False,
            'provider_type': self.provider_type,
            'embedding_model': self.embedding_model,
            'dimension': None,
            'error': None
        }

        with _suppress_litellm_debug():
            try:
                # If embedding_model is configured, test embeddings
                # Otherwise test LLM (for chat-only configurations)
                if self.embedding_model:
                    test_text = "Connection test"
                    embedding = self.generate_embedding(test_text)
                    result['available'] = True
                    result['dimension'] = len(embedding)
                else:
                    # Test LLM with a minimal completion
                    response = self.chat_completion(
                        messages=[{"role": "user", "content": "test"}],
                        temperature=0.0,
                        stream=False
                    )
                    if response.get('content') is not None:
                        result['available'] = True

            except ProviderUnavailableError as error:
                result['error'] = f"Provider unavailable: {error}"
            except APIKeyMissingError as error:
                result['error'] = f"API key missing: {error}"
            except Exception as error:
                result['error'] = f"Unexpected error: {error}"

        return result

    def validate_description(self, description: str) -> Dict[str, Any]:
        result = {
            'score': 0,
            'feedback': '',
            'valid': False,
            'error': None
        }

        if not description or not description.strip():
            result['error'] = "Description is empty"
            result['feedback'] = "Please provide a description for this collection"
            return result

        try:
            # Construct validation prompt
            prompt = f"""You are evaluating a description for a semantic search knowledge base collection.

Description to evaluate:
"{description}"

Score this description from 0-10 based on:
- Clarity: Is it clear what content is in this collection?
- Specificity: Does it describe the specific domain/topic?
- Usefulness: Will it help users understand what they can search for?

Provide your response in this EXACT format:
SCORE: [number 0-10]
FEEDBACK: [one sentence of constructive feedback]

Be concise and direct."""

            response = self._chat_completion_request(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
                tools=None,
                stream=False
            )

            if not response:
                raise AIProviderError("Invalid response from LLM: empty response")

            # LiteLLM returns a ModelResponse object - try attribute access first, then dict
            try:
                choices = response.choices
            except (AttributeError, TypeError):
                try:
                    choices = response['choices']  # type: ignore[index]
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from LLM: no choices")

            if not choices:
                raise AIProviderError("Invalid response from LLM: empty choices list")

            first_choice = choices[0]

            try:
                message = first_choice.message
            except (AttributeError, TypeError):
                try:
                    message = first_choice['message']  # type: ignore[index]
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from LLM: missing message")

            try:
                content = message.content
            except (AttributeError, TypeError):
                try:
                    content = message['content']  # type: ignore[index]
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from LLM: missing content")

            if not content:
                raise AIProviderError("Invalid response from LLM: empty content")

            response_text = content.strip()

            score_match = re.search(r'SCORE:\s*(\d+)', response_text, re.IGNORECASE)
            feedback_match = re.search(r'FEEDBACK:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)

            if score_match:
                score = int(score_match.group(1))
                result['score'] = min(10, max(0, score))  # Clamp to 0-10
                result['valid'] = result['score'] >= 7
            else:
                result['error'] = "Could not parse score from LLM response"

            if feedback_match:
                result['feedback'] = feedback_match.group(1).strip()
            else:
                result['feedback'] = response_text  # Use full response if format doesn't match

        except (AIProviderError, ProviderUnavailableError):
            # Re-raise our own exceptions unchanged
            raise
        except Exception as error:
            result['error'] = f"Validation failed: {error}"
            result['feedback'] = "Could not validate description due to an error"

        return result

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        if not messages:
            raise ValueError("Messages list cannot be empty")

        try:
            response = self._chat_completion_request(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                stream=stream
            )

            if stream:
                if isinstance(response, dict) and 'stream' in response:
                    return response
                return {'stream': response}

            if not response:
                raise AIProviderError("Invalid response from LLM: empty response")

            try:
                choices = response.choices
            except (AttributeError, TypeError):
                try:
                    choices = response['choices']
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from LLM: no choices")

            if not choices:
                raise AIProviderError("Invalid response from LLM: empty choices list")

            first_choice = choices[0]

            try:
                message = first_choice.message
            except (AttributeError, TypeError):
                try:
                    message = first_choice['message']
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from LLM: missing message")

            # Extract role from message
            try:
                role = message.role
            except (AttributeError, TypeError):
                try:
                    role = message['role']
                except (KeyError, TypeError):
                    role = 'assistant'  # Fallback to 'assistant' if role is missing

            result = {'role': role}

            try:
                content = message.content
            except (AttributeError, TypeError):
                try:
                    content = message['content']
                except (KeyError, TypeError):
                    content = None

            result['content'] = content

            try:
                tool_calls = message.tool_calls
            except (AttributeError, TypeError):
                try:
                    tool_calls = message.get('tool_calls')
                except (AttributeError, TypeError):
                    tool_calls = None

            if tool_calls:
                result['tool_calls'] = self._extract_tool_calls(tool_calls)

            try:
                finish_reason = first_choice.finish_reason
            except (AttributeError, TypeError):
                try:
                    finish_reason = first_choice.get('finish_reason')
                except (AttributeError, TypeError):
                    finish_reason = None

            if finish_reason:
                result['finish_reason'] = finish_reason

            return result

        except (AIProviderError, ProviderUnavailableError):
            raise
        except Exception as error:
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in ['connection', 'refused', 'unavailable', 'timeout']):
                raise ProviderUnavailableError(
                    f"{self.provider_type} provider is unavailable: {error}\n"
                    f"  Check that the service is running and accessible"
                ) from error
            elif 'rate limit' in error_str or 'quota' in error_str:
                raise AIProviderError(f"Rate limit exceeded: {error}") from error
            elif 'token' in error_str and 'limit' in error_str:
                raise AIProviderError(f"Token limit exceeded: {error}") from error
            else:
                raise AIProviderError(f"Chat completion failed: {error}") from error

    def chat_completion_streaming(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        if not messages:
            raise ValueError("Messages list cannot be empty")

        try:
            response = self._chat_completion_request(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                stream=True
            )

            if isinstance(response, dict):
                stream_source = response.get('stream')
            else:
                stream_source = response

            if stream_source is None:
                raise AIProviderError("Streaming response missing stream iterator")

            accumulated_content = []
            accumulated_tool_calls = []

            for chunk in stream_source:
                if not chunk:
                    continue

                try:
                    choices = chunk.choices
                except (AttributeError, TypeError):
                    try:
                        choices = chunk['choices']
                    except (KeyError, TypeError):
                        continue

                if not choices:
                    continue

                first_choice = choices[0]

                try:
                    delta = first_choice.delta
                except (AttributeError, TypeError):
                    try:
                        delta = first_choice['delta']
                    except (KeyError, TypeError):
                        continue

                chunk_data = {}

                try:
                    content = delta.content
                except (AttributeError, TypeError):
                    try:
                        content = delta.get('content')
                    except (AttributeError, TypeError):
                        content = None

                if content:
                    accumulated_content.append(content)
                    chunk_data['content'] = content

                try:
                    tool_calls = delta.tool_calls
                except (AttributeError, TypeError):
                    try:
                        tool_calls = delta.get('tool_calls')
                    except (AttributeError, TypeError):
                        tool_calls = None

                if tool_calls:
                    accumulated_tool_calls.extend(tool_calls)
                    chunk_data['tool_calls'] = tool_calls

                try:
                    finish_reason = first_choice.finish_reason
                except (AttributeError, TypeError):
                    try:
                        finish_reason = first_choice.get('finish_reason')
                    except (AttributeError, TypeError):
                        finish_reason = None

                if finish_reason:
                    chunk_data['finish_reason'] = finish_reason
                    chunk_data['full_content'] = ''.join(accumulated_content)
                    if accumulated_tool_calls:
                        chunk_data['full_tool_calls'] = self._extract_tool_calls(accumulated_tool_calls)

                if chunk_data:
                    yield chunk_data

        except (AIProviderError, ProviderUnavailableError):
            raise
        except Exception as error:
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in ['connection', 'refused', 'unavailable', 'timeout']):
                raise ProviderUnavailableError(
                    f"{self.provider_type} provider is unavailable: {error}\n"
                    f"  Check that the service is running and accessible"
                ) from error
            elif 'rate limit' in error_str or 'quota' in error_str:
                raise AIProviderError(f"Rate limit exceeded: {error}") from error
            elif 'token' in error_str and 'limit' in error_str:
                raise AIProviderError(f"Token limit exceeded: {error}") from error
            else:
                raise AIProviderError(f"Chat completion streaming failed: {error}") from error

    def _extract_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        extracted = []
        for tool_call in tool_calls:
            try:
                call_id = tool_call.id
            except (AttributeError, TypeError):
                try:
                    call_id = tool_call['id']
                except (KeyError, TypeError):
                    call_id = None

            try:
                function = tool_call.function
            except (AttributeError, TypeError):
                try:
                    function = tool_call['function']
                except (KeyError, TypeError):
                    continue

            try:
                function_name = function.name
            except (AttributeError, TypeError):
                try:
                    function_name = function['name']
                except (KeyError, TypeError):
                    continue

            try:
                arguments_str = function.arguments
            except (AttributeError, TypeError):
                try:
                    arguments_str = function['arguments']
                except (KeyError, TypeError):
                    arguments_str = '{}'

            extracted.append({
                'id': call_id,
                'type': 'function',
                'function': {
                    'name': function_name,
                    'arguments': arguments_str
                }
            })

        return extracted
