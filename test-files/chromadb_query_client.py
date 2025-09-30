#!/usr/bin/env python3
"""
Interactive ChromaDB Query Client for Bear Notes RAG System.

This tool provides an interactive interface to test semantic search capabilities
against the Bear Notes ChromaDB collection. Simulates the core functionality
that will be used in the MCP server for augmenting AI prompts.

Usage:
    python chromadb_query_client.py

Features:
- Interactive query loop with user input
- Real-time embedding generation for queries
- Semantic search with configurable result count
- Rich result formatting with note context
- Similarity score display for relevance assessment
"""

import sys
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../bear-notes-cag-data-creator'))

try:
    import chromadb
    from embedding import generate_embedding, initialize_embedding_service, EmbeddingError, OllamaServiceError
    from storage import initialize_chromadb_client, get_or_create_collection, ChromaDBConnectionError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're in the correct directory and dependencies are installed.")
    sys.exit(1)


class BearNotesQueryClient:
    """
    Interactive client for querying Bear Notes embeddings via ChromaDB.

    Simulates the core retrieval functionality for the MCP server by:
    1. Taking user queries as input
    2. Generating embeddings for queries
    3. Performing semantic search in ChromaDB
    4. Returning formatted results with note context
    """

    def __init__(
        self,
        chromadb_path: str = "../chromadb_data/bear_notes_embeddings",
        collection_name: str = "bear_notes_chunks",
        max_results: int = 3
    ):
        """
        Initialize the query client.

        Args:
            chromadb_path: Path to ChromaDB database
            collection_name: Name of the collection to query
            max_results: Maximum number of results to return per query
        """
        self.chromadb_path = chromadb_path
        self.collection_name = collection_name
        self.max_results = max_results
        self.client = None
        self.collection = None
        self.embedding_service_ready = False

    def initialize(self) -> bool:
        """
        Initialize ChromaDB connection and embedding service.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            print("🔧 Initializing ChromaDB query client...")
            print("=" * 60)

            # Initialize ChromaDB client
            print("📦 Connecting to ChromaDB...")
            self.client = initialize_chromadb_client(self.chromadb_path)

            # Get collection
            self.collection = get_or_create_collection(self.client, self.collection_name)

            # Check collection status
            count = self.collection.count()
            print(f"✅ Connected to collection '{self.collection_name}'")
            print(f"   📊 Total chunks available: {count:,}")

            if count == 0:
                print("⚠️  Warning: Collection is empty! You may need to run the full pipeline first.")
                return False

            # Initialize embedding service
            print("\n🧠 Initializing Ollama embedding service...")
            embedding_status = initialize_embedding_service()
            print(f"✅ Embedding service ready: {embedding_status['model_name']}")
            self.embedding_service_ready = True

            print("\n🎯 Query client initialized successfully!")
            print(f"   🔍 Ready to search {count:,} chunks")
            print(f"   📝 Max results per query: {self.max_results}")
            print()

            return True

        except (ChromaDBConnectionError, OllamaServiceError) as e:
            print(f"❌ Initialization failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected initialization error: {e}")
            return False

    def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for user query.

        Args:
            query: User's search query

        Returns:
            Embedding vector or None if generation fails
        """
        try:
            if not query.strip():
                return None

            embedding = generate_embedding(query.strip())
            return embedding

        except EmbeddingError as e:
            print(f"❌ Failed to generate query embedding: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected embedding error: {e}")
            return None

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        n_results: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for similar chunks using query embedding.

        Args:
            query_embedding: Embedding vector for the query
            n_results: Number of results to return (defaults to self.max_results)

        Returns:
            ChromaDB query results or None if search fails
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results or self.max_results,
                include=["documents", "metadatas", "distances"]
            )
            return results

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return None

    def format_search_results(self, results: Dict[str, Any], query: str) -> str:
        """
        Format search results for display.

        Args:
            results: ChromaDB query results
            query: Original user query

        Returns:
            Formatted results string
        """
        if not results or not results.get('documents'):
            return "🔍 No relevant chunks found for your query."

        documents = results['documents'][0]  # First query results
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]

        if not documents:
            return "🔍 No relevant chunks found for your query."

        output = []
        output.append(f"🎯 Found {len(documents)} relevant chunks for: '{query}'")
        output.append("=" * 60)

        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            # Calculate similarity score (1 - cosine distance)
            similarity = 1 - distance

            # Extract metadata
            note_title = metadata.get('title', 'Unknown Note')
            note_id = metadata.get('note_id', 'Unknown ID')
            chunk_index = metadata.get('chunk_index', 0)
            mod_date = metadata.get('modificationDate', 'Unknown Date')

            output.append(f"\n📄 Result #{i+1}")
            output.append(f"   📝 Note: {note_title}")
            output.append(f"   🔢 Chunk: {chunk_index}")
            output.append(f"   📅 Modified: {mod_date}")
            output.append(f"   🎯 Similarity: {similarity:.3f}")
            output.append(f"   📋 Content Preview:")

            # Show content preview (first 200 chars)
            preview = doc[:200] + "..." if len(doc) > 200 else doc
            content_lines = preview.split('\n')
            for line in content_lines[:3]:  # Show first 3 lines
                if line.strip():
                    output.append(f"      {line.strip()}")

            if len(content_lines) > 3:
                output.append(f"      ... (truncated)")

            output.append("-" * 40)

        return "\n".join(output)

    def run_interactive_loop(self):
        """
        Run the interactive query loop.
        """
        print("🚀 Bear Notes Interactive Query Client")
        print("=" * 60)
        print("Enter your queries to search through your Bear notes.")
        print("Type 'quit', 'exit', or 'q' to stop.")
        print("Type 'help' for more information.")
        print()

        while True:
            try:
                # Get user input
                query = input("🔍 Query: ").strip()

                # Handle special commands
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye! Thanks for using Bear Notes Query Client.")
                    break
                elif query.lower() == 'help':
                    self.show_help()
                    continue
                elif not query:
                    continue

                print(f"\n⏳ Searching for: '{query}'...")

                # Generate query embedding
                query_embedding = self.generate_query_embedding(query)
                if not query_embedding:
                    print("❌ Failed to generate embedding for query. Please try again.")
                    continue

                # Search for similar chunks
                results = self.search_similar_chunks(query_embedding)
                if not results:
                    print("❌ Search failed. Please try again.")
                    continue

                # Format and display results
                formatted_results = self.format_search_results(results, query)
                print(f"\n{formatted_results}")
                print()

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                print("Please try again or type 'quit' to exit.")

    def show_help(self):
        """Show help information."""
        help_text = """
📖 Bear Notes Query Client Help
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Purpose:
   Test semantic search capabilities against your Bear notes embeddings.
   Simulates the core functionality for the future MCP server.

🔍 How to Use:
   1. Type natural language queries about your notes
   2. The system will find the most relevant content chunks
   3. Results show similarity scores and note context

📊 Results Format:
   - Note Title: Which Bear note contains the chunk
   - Chunk Index: Position within the note
   - Similarity Score: How relevant (0.0 to 1.0)
   - Content Preview: First few lines of matching text

💡 Query Tips:
   - Use natural language: "machine learning projects"
   - Try specific terms: "Python code examples"
   - Ask questions: "how to deploy applications"
   - Use concepts: "productivity tips"

⚙️  Commands:
   - 'help': Show this help message
   - 'quit', 'exit', 'q': Exit the client

🔗 Integration Context:
   This client tests the same search logic that will power the MCP server
   for augmenting AI prompts with relevant note content.
        """
        print(help_text)


def main():
    """Main entry point for the interactive query client."""
    client = BearNotesQueryClient()

    # Initialize the client
    if not client.initialize():
        print("❌ Failed to initialize query client. Exiting.")
        sys.exit(1)

    # Run interactive loop
    try:
        client.run_interactive_loop()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()