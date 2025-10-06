# Instructions

I want to create vector embeddings for all my notes so that I can query an AI and get answers based on them using a RAG system.
I already have a python library tool that extract all my notes and returns them in the form of a python array with this shape:

```text
- title: Note title
- markdown: Note content in markdown format
- size: UTF-8 byte size of markdown content
- modificationDate: Last modification date in UTC ISO format
```

alternatively, data can be saved to a JSON file.

I found that the chromadb can be the easiest solution to implement (I had a look at postgres sql + vector db but the table configuration seems quite complex for me, I know something about SQL and relational databases but I'm not a database designer).

The AI system will be local: ollama with llama3.1:8b or gpt-oss:20b or gemma3:12b-it-qat.
The entire system won't need any internet connection, neither in preparing data, nor in answering the user prompts.

There are several unknowns in this project, this is what I expect should happen

1. get the data, from the original note parser or from its json output
2. create chunks
3. create vector embeddings
4. feed them somehow into chromadb

## Chunking

- decide chunk size - I read that it should be 800–1600 chars with an overlap of 10–20%
- keep atomic code blocks and tables, don't split them
- Keep semantic boundaries (headings, paragraphs, sentences).
- Carry heading path in metadata (e.g., ["Title", "H2", "H3"]) to reconstruct context.

## Embedding

- We are going to use a local AI for embeddings too: ollama mxbai-embed-large:latest.
- depending on the next steps, we may need to normalize vectors, I read somewhere

## feed chromadb

- I read somewhere that I should batch 32–128 chunks per call
- Persistent client (folder on disk).
- distance metric hnsw:space="cosine" (with normalized embeddings) maybe? need to understand if it is the right choice
- Create a stable chunk id, for example = sha256(note_id | modificationDate | chunk_index)
- this operation will be periodically re-executed (e.g. once a week), initially we will recreate the data entirely, then - in the future - we may evaluate to replace only changed notes
- metadata to store:
  - note_id (your own stable id or path)
  - title
  - modificationDate
  - size
  - chunk_index
  - heading_path
  - char_start, char_end (optional but great for provenance)
  - maybe hash (raw chunk sha256) to skip re-embedding identical chunks

Example of a very simple script doing something similar: ../test-files/test-chunking.py

## Additional Requirements from PRD Discussion

### Data Input Approach
- **Input format**: JSON file from bear-notes-parser (e.g., "Bear Notes 2025-09-20 at 08.49.json")
- **Rationale**: Start with JSON file approach for better separation of concerns, debugging, and data persistence
- **Future enhancement**: Could add hybrid approach (JSON or direct Bear backup parsing) once pipeline is stable

### User & Usage Pattern
- **Target user**: Personal use only (single user)
- **Processing schedule**: Manual runs approximately weekly (no automation required)
- **Scope**: Database creation and population tool only (not the query/client application)

### Error Handling & Feedback
- **Error strategy**: Skip failed notes, continue processing, report failures at the end
- **Progress feedback**: Show progress percentage and current note being processed
- **Data validation**: Minimal - trust the bear-notes-parser output quality

### Chunk Size Strategy
- **Approach**: Test different chunk sizes and select optimal one
- **Target range**: 300-500 tokens initially, with configurable overlap
- **Evaluation criteria**: TBD (need to determine "best" metrics)

### Output & Reporting
- **Primary output**: Populate ChromaDB with vector embeddings
- **Additional output**: Create summary report of processing results
- **Reporting includes**: Number of notes processed, chunks created, any failures encountered
