from __future__ import annotations


class MinervaError(Exception):
    default_exit_code = 1

    def __init__(self, message: str = "", *, exit_code: int | None = None) -> None:
        super().__init__(message)
        self.exit_code = self.default_exit_code if exit_code is None else exit_code


class GracefulExit(MinervaError):
    default_exit_code = 0


class ConfigError(MinervaError):
    pass


class ConfigValidationError(ConfigError):
    pass


class ValidationError(MinervaError):
    pass


class IndexingError(MinervaError):
    pass


class JsonLoaderError(IndexingError):
    pass


class ChunkingError(IndexingError):
    pass


class StorageError(IndexingError):
    pass


class ChromaDBConnectionError(StorageError):
    pass


class IncrementalUpdateError(IndexingError):
    pass


class EmbeddingError(IndexingError):
    pass


class ProviderError(MinervaError):
    pass


class AIProviderError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ServerError(MinervaError):
    pass


class StartupValidationError(ServerError):
    pass


class CollectionDiscoveryError(ServerError):
    pass


class ContextRetrievalError(ServerError):
    pass


class ChatError(MinervaError):
    pass


class ChatEngineError(ChatError):
    pass


class ChatConfigError(ChatError):
    pass


class APIKeyMissingError(ProviderError):
    pass


EXCEPTION_EXIT_CODES = {
    MinervaError: 1,
    GracefulExit: 0,
    ConfigError: 1,
    ConfigValidationError: 1,
    ValidationError: 1,
    IndexingError: 1,
    JsonLoaderError: 1,
    ChunkingError: 1,
    StorageError: 1,
    ChromaDBConnectionError: 1,
    IncrementalUpdateError: 1,
    EmbeddingError: 1,
    ProviderError: 1,
    AIProviderError: 1,
    ProviderUnavailableError: 1,
    ServerError: 1,
    StartupValidationError: 1,
    CollectionDiscoveryError: 1,
    ContextRetrievalError: 1,
    ChatError: 1,
    ChatEngineError: 1,
    ChatConfigError: 1,
    APIKeyMissingError: 1,
}


def resolve_exit_code(error: MinervaError) -> int:
    return getattr(error, "exit_code", EXCEPTION_EXIT_CODES.get(type(error), 1))
