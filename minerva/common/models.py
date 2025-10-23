from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    id: str
    content: str

    # Metadata inherited from the parent note
    noteId: str
    title: str
    modificationDate: str
    creationDate: str
    size: int

    # Position within the note (0-indexed)
    chunkIndex: int

    def __post_init__(self):
        if not self.id:
            raise ValueError("Chunk ID cannot be empty")
        if not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.chunkIndex < 0:
            raise ValueError("Chunk index must be non-negative")


@dataclass(frozen=True)
class ChunkWithEmbedding:
    # Original chunk data (preserved exactly)
    chunk: Chunk

    # AI-generated embedding vector (typically 1024 dimensions for mxbai-embed-large)
    embedding: List[float]

    def __post_init__(self):
        if not self.embedding:
            raise ValueError("Embedding vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in self.embedding):
            raise ValueError("Embedding must contain only numeric values")

    # Convenience properties to access chunk fields directly
    @property
    def id(self) -> str:
        return self.chunk.id

    @property
    def content(self) -> str:
        return self.chunk.content

    @property
    def noteId(self) -> str:
        return self.chunk.noteId

    @property
    def title(self) -> str:
        return self.chunk.title

    @property
    def modificationDate(self) -> str:
        return self.chunk.modificationDate

    @property
    def creationDate(self) -> str:
        return self.chunk.creationDate

    @property
    def size(self) -> int:
        return self.chunk.size

    @property
    def chunkIndex(self) -> int:
        return self.chunk.chunkIndex


# Type aliases for better readability in function signatures
ChunkList = List[Chunk]
ChunkWithEmbeddingList = List[ChunkWithEmbedding]