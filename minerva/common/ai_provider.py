import os
import re
from typing import List, Dict, Any, Optional
import numpy as np

from minerva.common.ai_config import AIProviderConfig, APIKeyMissingError


class AIProviderError(Exception):
    pass


class ProviderUnavailableError(AIProviderError):
    pass


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class AIProvider:
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.api_key = config.resolve_api_key()
        self.provider_type = config.provider_type
        self.embedding_model = config.embedding_model
        self.llm_model = config.llm_model
        self.base_url = config.base_url

        try:
            import litellm
            self.litellm = litellm
        except ImportError:
            raise AIProviderError(
                "LiteLLM is not installed.\n"
                "  Install with: pip install litellm"
            )

        self._configure_litellm()

    def _configure_litellm(self):
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
            os.environ['OLLAMA_API_BASE'] = self.base_url

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
            # Get model name in LiteLLM format
            model_name = self._get_model_name_for_litellm(self.embedding_model, for_embedding=True)

            # Call LiteLLM's embedding function
            response = self.litellm.embedding(
                model=model_name,
                input=[text]
            )

            if not response:
                raise AIProviderError("Invalid response from provider: empty response")

            # LiteLLM returns an EmbeddingResponse object - try attribute access first, then dict
            try:
                data = response.data
            except (AttributeError, TypeError):
                try:
                    data = response['data']  # type: ignore[index]
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from provider: missing embedding data")

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
            # Get model name in LiteLLM format
            model_name = self._get_model_name_for_litellm(self.embedding_model, for_embedding=True)

            # Call LiteLLM's embedding function with batch input
            response = self.litellm.embedding(
                model=model_name,
                input=texts
            )

            if not response:
                raise AIProviderError("Invalid response from provider: empty response")

            # LiteLLM returns an EmbeddingResponse object - try attribute access first, then dict
            try:
                data = response.data
            except (AttributeError, TypeError):
                try:
                    data = response['data']  # type: ignore[index]
                except (KeyError, TypeError):
                    raise AIProviderError("Invalid response from provider: missing embedding data")

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

        try:
            # Try to generate a test embedding
            test_text = "Connection test"
            embedding = self.generate_embedding(test_text)

            # If we got here, the provider is available
            result['available'] = True
            result['dimension'] = len(embedding)

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
            # Get model name in LiteLLM format
            model_name = self._get_model_name_for_litellm(self.llm_model, for_embedding=False)

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

            # Call LLM
            response = self.litellm.completion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more consistent scoring
                max_tokens=150
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
