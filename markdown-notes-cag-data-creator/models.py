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
        """Validate chunk data on creation."""
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
        """Validate embedding data on creation."""
        if not self.embedding:
            raise ValueError("Embedding vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in self.embedding):
            raise ValueError("Embedding must contain only numeric values")

    # Convenience properties to access chunk fields directly
    @property
    def id(self) -> str:
        """Access chunk ID directly."""
        return self.chunk.id

    @property
    def content(self) -> str:
        """Access chunk content directly."""
        return self.chunk.content

    @property
    def noteId(self) -> str:
        """Access note ID directly."""
        return self.chunk.noteId

    @property
    def title(self) -> str:
        """Access note title directly."""
        return self.chunk.title

    @property
    def modificationDate(self) -> str:
        """Access modification date directly."""
        return self.chunk.modificationDate

    @property
    def creationDate(self) -> str:
        """Access creation date directly."""
        return self.chunk.creationDate

    @property
    def size(self) -> int:
        """Access note size directly."""
        return self.chunk.size

    @property
    def chunkIndex(self) -> int:
        """Access chunk index directly."""
        return self.chunk.chunkIndex


# Type aliases for better readability in function signatures
ChunkList = List[Chunk]
ChunkWithEmbeddingList = List[ChunkWithEmbedding]