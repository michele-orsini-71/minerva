#!/usr/bin/env python3
"""
Immutable data models for the Bear Notes RAG pipeline.

This module defines the core data structures that flow through the pipeline:
- Chunk: Immutable text chunk after content splitting
- ChunkWithEmbedding: Immutable chunk with AI-generated embedding vector

The design uses composition and immutability to ensure clean type transitions
between pipeline stages without data conversion overhead.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    """
    Immutable chunk of text content from a Bear note.

    Created by the chunking stage and flows through the embedding
    and storage stages. All fields are immutable to ensure data
    integrity throughout the pipeline.
    """
    # Unique identifier for this chunk
    id: str

    # The actual text content of the chunk
    content: str

    # Metadata inherited from the parent note
    note_id: str
    title: str
    modificationDate: str
    creationDate: str
    size: int

    # Position within the note (0-indexed)
    chunk_index: int

    def __post_init__(self):
        """Validate chunk data on creation."""
        if not self.id:
            raise ValueError("Chunk ID cannot be empty")
        if not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.chunk_index < 0:
            raise ValueError("Chunk index must be non-negative")


@dataclass(frozen=True)
class ChunkWithEmbedding:
    """
    Immutable chunk with AI-generated embedding vector.

    Created by the embedding stage and consumed by the storage stage.
    Uses composition to preserve the original Chunk data exactly,
    while adding the embedding as new information.
    """
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
    def note_id(self) -> str:
        """Access note ID directly."""
        return self.chunk.note_id

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
    def chunk_index(self) -> int:
        """Access chunk index directly."""
        return self.chunk.chunk_index

    def to_storage_dict(self) -> dict:
        """
        Convert to dictionary format for ChromaDB storage.

        Returns a dictionary with all fields needed for ChromaDB insertion,
        eliminating the need for complex data conversion in the storage layer.
        """
        return {
            'id': self.id,
            'content': self.content,
            'embedding': self.embedding,
            # Metadata fields
            'note_id': self.note_id,
            'title': self.title,
            'modificationDate': self.modificationDate,
            'creationDate': self.creationDate,
            'size': self.size,
            'chunk_index': self.chunk_index
        }


# Type aliases for better readability in function signatures
ChunkList = List[Chunk]
ChunkWithEmbeddingList = List[ChunkWithEmbedding]