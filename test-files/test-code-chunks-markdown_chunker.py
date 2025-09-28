#!/usr/bin/env python3
"""Quick test for markdown-chunker with code blocks."""

import json
from markdown_chunker import MarkdownChunkingStrategy

# Load notes
with open('../test-data/Bear Notes 2025-09-20 at 08.49.json', 'r') as f:
    notes = json.load(f)

# Find a note with code blocks
code_note = None
for note in notes:
    if '```' in note['markdown'] and len(note['markdown']) > 500:
        code_note = note
        break

if code_note:
    print('Testing with code block note:')
    print('Title:', code_note['title'])
    print('Length:', len(code_note['markdown']), 'chars')
    print()

    # Test chunking
    strategy = MarkdownChunkingStrategy(
        add_metadata=False,
        soft_max_len=800,
        hard_max_len=1200,
        heading_based_chunking=True,
        remove_duplicates=False  # Disable to see what's happening
    )
    chunks = strategy.chunk_markdown(code_note['markdown'])

    print(f'Created {len(chunks)} chunks:')
    for i, chunk in enumerate(chunks):
        print(f'\nChunk {i+1} ({len(chunk)} chars):')
        preview = chunk[:200] + '...' if len(chunk) > 200 else chunk
        print(preview)
        print('-'*40)
else:
    print('No suitable code note found')