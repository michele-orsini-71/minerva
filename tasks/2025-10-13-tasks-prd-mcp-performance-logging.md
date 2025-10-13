## Relevant Files

- `markdown-notes-mcp-server/utils/__init__.py` - Python package initialization file for the utils module.
- `markdown-notes-mcp-server/utils/performance.py` - Core performance timer utility with context manager for timing measurements and JSON summary generation.
- `markdown-notes-mcp-server/search_tools.py` - Primary integration point: add timing instrumentation to the `search_knowledge_base` function and all search pipeline operations.
- `markdown-notes-mcp-server/context_retrieval.py` - Secondary integration point: add timing to context retrieval functions (`get_enhanced_content`, `get_full_note_content`).
- `markdown-notes-mcp-server/tests/test_performance.py` - Unit tests for the performance timer utility.

### Notes

- Unit tests should typically be placed alongside the code files they are testing or in the `tests/` directory.
- Use `pytest markdown-notes-mcp-server/tests/` to run all tests.
- Performance logs will appear in the existing MCP server logs at `/Users/michele/Library/Logs/Claude/`.
- Manual testing can be done by running the MCP server and executing search queries through the Claude Desktop client.

## Tasks

- [x] 1.0 Create core performance timer utility module
  - [x] 1.1 Create `markdown-notes-mcp-server/utils/` directory
  - [x] 1.2 Create `markdown-notes-mcp-server/utils/__init__.py` file (empty or with exports)
  - [x] 1.3 Create `markdown-notes-mcp-server/utils/performance.py` with timer context manager implementation
  - [x] 1.4 Implement timer context manager using `@contextmanager` decorator with `time.perf_counter()` for high-resolution timing
  - [x] 1.5 Add try/finally block to ensure duration is logged even if wrapped code raises exceptions
  - [x] 1.6 Add logging output in format `[PERF] <operation>: <duration>ms` with 2 decimal places
  - [x] 1.7 Support optional logger parameter (create default stderr logger if not provided)
  - [x] 1.8 Add comprehensive docstrings with usage examples showing how to use the timer
  - [x] 1.9 Create helper function to build JSON summary dictionaries with timing data and query characteristics
  - [x] 1.10 Add helper function to log JSON summaries in format `[PERF-JSON] {...}` on single line

- [ ] 2.0 Instrument search_tools.py with performance timing
  - [ ] 2.1 Import timer utility and logging module at top of `search_tools.py`
  - [ ] 2.2 Add logger instance creation (module-level or function-level)
  - [ ] 2.3 Wrap entire `search_knowledge_base` function body with timer for "Total search operation"
  - [ ] 2.4 Add timer around ChromaDB client initialization (line ~69)
  - [ ] 2.5 Add timer around collection validation (line ~72)
  - [ ] 2.6 Add timer around query embedding generation (lines ~86-87) - this is likely bottleneck #1
  - [ ] 2.7 Add timer around ChromaDB query operation (lines ~107-111) - this is likely bottleneck #2
  - [ ] 2.8 Add timer around result formatting loop (lines ~114-128)
  - [ ] 2.9 Capture query characteristics: query length (characters), collection name, context mode, max_results
  - [ ] 2.10 Capture result characteristics: number of results returned

- [ ] 3.0 Instrument context_retrieval.py with performance timing
  - [ ] 3.1 Import timer utility and logging module at top of `context_retrieval.py`
  - [ ] 3.2 Add logger instance creation for the module
  - [ ] 3.3 Wrap entire `apply_context_mode` function with timer for "Context retrieval total"
  - [ ] 3.4 Add timer around ChromaDB query in `get_enhanced_content` (lines ~32-41)
  - [ ] 3.5 Add timer around chunk sorting and content building in `get_enhanced_content` (lines ~48-68)
  - [ ] 3.6 Add timer around ChromaDB query in `get_full_note_content` (lines ~87-90)
  - [ ] 3.7 Add timer around chunk sorting and content building in `get_full_note_content` (lines ~96-113)
  - [ ] 3.8 Capture total chunks retrieved for enhanced/full_note modes

- [ ] 4.0 Add JSON summary logging to search pipeline
  - [ ] 4.1 Collect all timing measurements into a dictionary at end of `search_knowledge_base` function
  - [ ] 4.2 Build JSON summary structure with: operation name, query characteristics (length, collection, context_mode, max_results)
  - [ ] 4.3 Add result characteristics to JSON: results_returned count, total_chunks retrieved
  - [ ] 4.4 Add timing breakdown: total, embedding, search, context (and sub-operations if available)
  - [ ] 4.5 Add ISO timestamp to JSON summary using `datetime.utcnow().isoformat()`
  - [ ] 4.6 Log JSON summary using helper function in single line format `[PERF-JSON] {...}`
  - [ ] 4.7 Ensure JSON is valid and can be parsed (all values are serializable)

- [ ] 5.0 Manual validation and testing
  - [ ] 5.1 Start the MCP server with instrumented code
  - [ ] 5.2 Execute test query with `chunk_only` mode and verify timing logs appear
  - [ ] 5.3 Execute test query with `enhanced` mode and verify enhanced context timing appears
  - [ ] 5.4 Execute test query with `full_note` mode and verify full note timing appears
  - [ ] 5.5 Verify all timing values are reasonable (non-zero, positive, in expected ms range)
  - [ ] 5.6 Verify JSON summary is valid and parseable (use `json.loads()` or jq on log output)
  - [ ] 5.7 Verify JSON contains all required fields: query characteristics, result characteristics, timing breakdown, timestamp
  - [ ] 5.8 Analyze 3-5 test queries to confirm bottleneck can be identified in < 5 minutes
  - [ ] 5.9 Verify existing search functionality still works correctly (no broken behavior)
  - [ ] 5.10 Document any observed performance patterns or bottlenecks discovered during testing
