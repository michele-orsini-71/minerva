#!/usr/bin/env python3

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "markdown-notes-cag-data-creator"))

import chromadb

def main():
    client = chromadb.PersistentClient(path='../chromadb_data')

    print("Available collections:")
    collections = client.list_collections()
    for coll in collections:
        print(f"  - {coll.name}")

    if not collections:
        print("\nNo collections found!")
        return

    # Get first collection
    collection = collections[0]
    print(f"\nInspecting collection: {collection.name}")

    # Get a few chunks
    results = collection.get(limit=5, include=['metadatas', 'documents'])

    print(f"\nFound {len(results['ids'])} chunks\n")

    for i in range(min(3, len(results['ids']))):
        chunk_id = results['ids'][i]
        metadata = results['metadatas'][i]
        content_preview = results['documents'][i][:80] + "..." if len(results['documents'][i]) > 80 else results['documents'][i]

        print(f"Chunk {i+1}:")
        print(f"  ID: {chunk_id}")
        print(f"  Title: {metadata.get('title')}")
        print(f"  ChunkIndex: {metadata.get('chunkIndex')}")
        print(f"  adjacent_chunk_ids: {metadata.get('adjacent_chunk_ids')}")
        print(f"  Content: {content_preview}")
        print()

if __name__ == "__main__":
    main()
