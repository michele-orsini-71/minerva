#!/usr/bin/env python3
"""
Test script for multilingual embedding capabilities.

This script tests how well the current mxbai-embed-large model handles
different languages and provides insights for multilingual Bear Notes.
"""

import sys
import os
from typing import List, Dict, Any
import numpy as np

# Note: Since packages are now CLI-only, we need to import modules directly for testing
# This is fine for development scripts that need to access internal functionality

# Add RAG data creator path for development/testing access to internal modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../bear-notes-cag-data-creator'))

try:
    from embedding import generate_embedding, initialize_embedding_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're in the correct directory and dependencies are installed.")
    sys.exit(1)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)

    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def test_multilingual_embeddings():
    """Test embedding generation and similarity across different languages."""

    print("🌍 Testing Multilingual Embedding Capabilities")
    print("=" * 60)

    # Initialize embedding service
    try:
        status = initialize_embedding_service()
        print(f"✅ Embedding service ready: {status['model_name']}")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize embedding service: {e}")
        return False

    # Test phrases in different languages - all expressing "machine learning"
    test_phrases = {
        "English": "machine learning algorithms and artificial intelligence",
        "Spanish": "algoritmos de aprendizaje automático e inteligencia artificial",
        "French": "algorithmes d'apprentissage automatique et intelligence artificielle",
        "German": "algorithmen für maschinelles lernen und künstliche intelligenz",
        "Italian": "algoritmi di apprendimento automatico e intelligenza artificiale",
        "Portuguese": "algoritmos de aprendizado de máquina e inteligência artificial",
        "Russian": "алгоритмы машинного обучения и искусственный интеллект",
        "Chinese": "机器学习算法和人工智能",
        "Japanese": "機械学習アルゴリズムと人工知能",
        "Arabic": "خوارزميات التعلم الآلي والذكاء الاصطناعي"
    }

    print("📝 Test phrases (all about 'machine learning and AI'):")
    for lang, phrase in test_phrases.items():
        print(f"   {lang:12}: {phrase}")
    print()

    # Generate embeddings
    print("🧠 Generating embeddings...")
    embeddings = {}

    for lang, phrase in test_phrases.items():
        try:
            embedding = generate_embedding(phrase)
            embeddings[lang] = embedding
            print(f"   ✅ {lang:12}: {len(embedding)} dimensions")
        except Exception as e:
            print(f"   ❌ {lang:12}: Failed - {e}")
            embeddings[lang] = None

    print()

    # Calculate similarity matrix
    print("🎯 Calculating cross-language similarities:")
    print("   (Higher values = more similar semantic meaning)")
    print()

    english_embedding = embeddings.get("English")
    if not english_embedding:
        print("❌ English embedding failed - cannot compare")
        return False

    similarities = {}
    for lang, embedding in embeddings.items():
        if embedding:
            similarity = cosine_similarity(english_embedding, embedding)
            similarities[lang] = similarity

    # Sort by similarity to English
    sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

    print("📊 Similarity to English (1.0 = identical, 0.0 = completely different):")
    for lang, similarity in sorted_similarities:
        status = "🟢" if similarity > 0.8 else "🟡" if similarity > 0.6 else "🔴"
        print(f"   {status} {lang:12}: {similarity:.4f}")

    print()

    # Analysis and recommendations
    analyze_results(similarities)

    return True


def analyze_results(similarities: Dict[str, float]):
    """Analyze multilingual results and provide recommendations."""

    print("📋 Analysis & Recommendations:")
    print("=" * 60)

    # Categorize performance
    excellent = [lang for lang, sim in similarities.items() if sim > 0.8]
    good = [lang for lang, sim in similarities.items() if 0.6 < sim <= 0.8]
    poor = [lang for lang, sim in similarities.items() if sim <= 0.6]

    if excellent:
        print(f"🟢 Excellent support (>0.8): {', '.join(excellent)}")
    if good:
        print(f"🟡 Good support (0.6-0.8): {', '.join(good)}")
    if poor:
        print(f"🔴 Limited support (<0.6): {', '.join(poor)}")

    print()
    print("💡 Recommendations for multilingual Bear Notes:")
    print()

    if len(poor) > len(excellent):
        print("⚠️  Current model (mxbai-embed-large) has limited multilingual support:")
        print("   - Works best for English and similar European languages")
        print("   - May struggle with non-Latin scripts (Arabic, Chinese, etc.)")
        print()
        print("🔄 Consider switching to better multilingual models:")
        print("   - Qwen3-Embedding-8B (top MTEB multilingual performance)")
        print("   - EmbeddingGemma (Google, 100+ languages)")
        print("   - Granite-Embedding-Multilingual")
        print()
        print("📦 To switch models:")
        print("   ollama pull qwen3-embedding")
        print("   # Update EMBED_MODEL in embedding.py")
    else:
        print("✅ Current model shows reasonable multilingual support")
        print("   - Should work well for mixed-language note collections")
        print("   - Cross-language queries may find relevant content")

    print()
    print("🏗️  Architecture recommendations:")
    print("   1. Language Detection: Add language metadata to chunks")
    print("   2. Query Routing: Detect query language and weight results")
    print("   3. Separate Collections: Consider language-specific collections")
    print("   4. Fallback Strategy: Use translation API for unsupported languages")

    print()
    print("🎯 Best practices for multilingual RAG:")
    print("   - Test with your actual note languages")
    print("   - Monitor retrieval quality across languages")
    print("   - Consider hybrid approaches (keywords + semantic)")
    print("   - Add language filters to search interface")


if __name__ == "__main__":
    success = test_multilingual_embeddings()
    if not success:
        sys.exit(1)