# PRD: MCP Server Performance Logging

## Introduction/Overview

This feature adds performance logging capabilities to the MCP (Model Context Protocol) server to identify bottlenecks in the semantic search pipeline. The MCP server currently provides semantic search across markdown note collections, but it's unclear which operations are causing slowness - query embedding generation, ChromaDB vector search, or context retrieval. This feature will instrument key operations with timing measurements to enable rapid performance analysis.

**Problem Statement:** When users perform semantic searches through the MCP server, responses can be slow, but there's no visibility into which stage of the pipeline is responsible for the delay. This makes optimization difficult and prevents informed decision-making about infrastructure improvements.

**Goal:** Enable rapid identification (< 5 minutes of log analysis) of performance bottlenecks in the search pipeline through structured timing measurements, while maintaining zero external dependencies and minimal code complexity.

## Goals

1. **Rapid Bottleneck Identification**: Enable identification of the slowest operation in the search pipeline within 5 minutes of log analysis
2. **Comprehensive Coverage**: Capture timing data for query embedding generation, ChromaDB vector search, and context retrieval operations
3. **Investigation-Ready Logging**: Provide both human-readable timestamps and structured JSON summaries for flexible analysis
4. **Zero Performance Impact Concerns**: Since this is for investigation purposes, prioritize data completeness over minimal overhead
5. **Maintainable Implementation**: Use clean, reusable utility code (context managers) that's easy to understand and extend
6. **Preserve Existing Functionality**: Add logging without breaking current MCP server behavior or existing log output

## User Stories

1. **As a developer investigating search slowness**, I want to see how long each operation takes so that I can identify which component to optimize first.

2. **As a developer comparing different configurations**, I want to see timing data for different query characteristics (collection name, context mode, query length) so that I can understand performance patterns.

3. **As a developer debugging a specific slow query**, I want detailed timing breakdowns for all sub-operations so that I can pinpoint the exact bottleneck.

4. **As a developer analyzing logs after testing**, I want structured JSON summaries at the end of each search operation so that I can easily parse and aggregate timing data.

5. **As a maintainer of the MCP server**, I want performance logging code to be simple and self-contained so that it doesn't add maintenance burden or complexity.

## Functional Requirements

### Core Timing Infrastructure

1. The system must provide a timer context manager utility that automatically measures elapsed time for code blocks
2. The timer context manager must use `time.perf_counter()` for high-resolution timing measurements
3. The timer must log both a start marker and duration upon completion
4. The timer must write to the existing stderr logging stream (captured by MCP client logs)
5. The timer must support nested timing for hierarchical operation tracking

### Search Pipeline Instrumentation

6. The system must time the complete `search_knowledge_base` operation from start to finish
7. The system must separately time query embedding generation (LiteLLM API call)
8. The system must separately time the ChromaDB vector search query
9. The system must separately time context retrieval operations (enhanced/full_note modes)
10. For enhanced context mode, the system must time the additional ChromaDB query for surrounding chunks
11. For full_note mode, the system must time the ChromaDB query for all note chunks
12. The system must time result formatting and processing operations

### Contextual Information Capture

13. The system must log query characteristics including: query length (characters), collection name, context mode, and max_results parameter
14. The system must log result characteristics including: number of results returned and total chunks retrieved (for context modes)
15. The system must include these characteristics in both human-readable logs and structured JSON summaries

### Output Format

16. The system must output human-readable timing messages in the format: `[PERF] <operation>: <duration>ms`
17. The system must output a structured JSON summary at the end of each search operation containing:
    - All timing measurements
    - Query characteristics
    - Result characteristics
    - Total operation time
18. The JSON summary must be on a single line prefixed with `[PERF-JSON]` for easy filtering
19. All timing measurements must be reported in milliseconds with 2 decimal places of precision

### Integration Requirements

20. The performance logging utility must be implemented in a new module: `markdown-notes-mcp-server/utils/performance.py`
21. The timer context manager must integrate with the existing `logging` module
22. Performance logs must use the INFO log level for normal operation timing
23. Performance logs must appear in the existing MCP server logs at `/Users/michele/Library/Logs/Claude/`
24. The implementation must not require any new external dependencies beyond Python standard library

### Code Quality Requirements

25. The timer utility must handle exceptions gracefully (still log duration even if wrapped code raises)
26. The timer utility must be thoroughly commented with docstrings explaining usage
27. The implementation must include usage examples in comments or docstrings
28. Variable names and function signatures must be clear and self-explanatory

## Non-Goals (Out of Scope)

1. **Log Rotation/Cleanup**: This feature will not implement automatic log file rotation or cleanup strategies. Logs will accumulate in the standard MCP log location managed by Claude Desktop.

2. **Separate Performance Log File**: Performance data will be written to the existing MCP log stream (stderr), not a separate dedicated performance log file. This avoids file management complexity.

3. **Performance Monitoring Dashboard**: This feature will not include any visualization, graphing, or real-time monitoring dashboard. Analysis will be done by examining log files.

4. **Historical Performance Tracking**: This feature will not track performance trends over time or store historical statistics. It's focused on immediate investigation of current performance.

5. **Configurable Logging Levels**: This feature will not include environment variables or config options to enable/disable performance logging. It will be always-on since the overhead is acceptable for investigation purposes.

6. **System Resource Monitoring**: This feature will not capture CPU usage, memory consumption, or other system-level metrics. Focus is purely on operation timing.

7. **Collection Discovery/Startup Timing**: This feature will not instrument the server startup sequence or collection discovery process. Focus is on the search pipeline performance.

8. **Provider Initialization Timing**: This feature will not measure AI provider initialization or validation timing at startup.

9. **Result Formatting Detailed Breakdown**: While total result formatting time will be captured, this feature will not break down individual result processing steps within the formatting loop.

10. **External Dependencies**: This feature will not add any external monitoring libraries (Prometheus, OpenTelemetry, etc.).

## Design Considerations

### Timer Context Manager Design

The core utility will be a context manager that can be used like this:

```python
from utils.performance import timer

with timer("Query embedding generation", logger=logger):
    query_embedding = provider.generate_embedding(query)
```

This will automatically:
- Log start of operation: `[PERF] Query embedding generation: started`
- Capture high-resolution timing
- Log completion: `[PERF] Query embedding generation: 234.56ms`

### JSON Summary Structure

At the end of each search operation, a single-line JSON summary will be logged:

```json
[PERF-JSON] {"operation":"search_knowledge_base","query_length":45,"collection":"bear_notes","context_mode":"enhanced","max_results":5,"results_returned":5,"total_chunks":15,"timing":{"total":1234.56,"embedding":234.56,"search":456.78,"context":543.22},"timestamp":"2025-10-13T14:23:45.123456Z"}
```

### File Locations

- **New utility module**: `markdown-notes-mcp-server/utils/performance.py`
- **Modified files**:
  - `markdown-notes-mcp-server/search_tools.py` (add timing to search pipeline)
  - `markdown-notes-mcp-server/context_retrieval.py` (add timing to context operations)
- **Log output**: `/Users/michele/Library/Logs/Claude/` (existing MCP log location)

### Integration Points

The timer utility will integrate with:
1. Existing `logging` module (use provided logger or create default)
2. `search_tools.py` - primary integration point for search pipeline
3. `context_retrieval.py` - secondary integration for context modes

## Technical Considerations

### Python Standard Library Dependencies
- `time.perf_counter()` for high-resolution timing
- `logging` module for output
- `json` module for structured summaries
- `contextlib.contextmanager` for context manager decorator
- `datetime` for ISO timestamps

### Exception Handling
The timer context manager must use a try/finally pattern to ensure duration is logged even if the wrapped operation raises an exception:

```python
try:
    yield
finally:
    duration = time.perf_counter() - start_time
    logger.info(f"[PERF] {operation_name}: {duration*1000:.2f}ms")
```

### Nested Timing Support
The timer should support nesting, where inner timers measure sub-operations:

```
[PERF] search_knowledge_base: started
[PERF]   Query embedding generation: 234.56ms
[PERF]   ChromaDB vector search: 456.78ms
[PERF]   Context retrieval: 543.22ms
[PERF] search_knowledge_base: 1234.56ms
```

Indentation for nested operations can be achieved by tracking nesting depth or simply not worrying about it for the MVP (all operations at same indentation level is acceptable).

### Existing Code Compatibility
- Must not modify function signatures
- Must not break existing error handling
- Must not interfere with existing logging (use same logger instances)

## Success Metrics

### Primary Success Criterion
**Time to identify bottleneck**: A developer should be able to identify which operation (embedding, search, or context retrieval) is the slowest by examining logs for < 5 minutes.

**Measurement**: After running 3-5 test queries and examining the logs, the developer should be able to state definitively: "The bottleneck is [X] operation, which takes approximately [Y]ms on average."

### Implementation Quality Metrics
- **Zero new external dependencies**: Verified by checking requirements.txt/pip list shows no new packages
- **No broken functionality**: All existing MCP server tests pass (if tests exist), manual testing shows search still works
- **Code maintainability**: A junior developer can understand the timer utility code and add timing to a new function in < 10 minutes

## Open Questions

1. **Nesting depth indication**: Should nested timers show visual indentation in logs, or is flat output acceptable?
   - **Initial decision**: Flat output is acceptable for MVP. Can enhance later if needed.

2. **JSON summary placement**: Should the JSON summary be logged in the main `search_knowledge_base` function or in a separate logging call in `server.py`?
   - **Initial decision**: Log in `search_tools.py` at the end of `search_knowledge_base()` for encapsulation.

3. **Timing granularity for result formatting**: Should we time each individual result processing, or just the overall formatting loop?
   - **Initial decision**: Overall formatting loop only - individual results would add noise without much benefit.

4. **Logger instance**: Should the timer utility create its own logger instance or always require one to be passed in?
   - **Initial decision**: Accept optional logger parameter, create default stderr logger if not provided.

5. **Startup operations**: If startup operations (collection discovery, provider init) are found to be slow during investigation, should we add timing there too?
   - **Initial decision**: Out of scope for initial PRD. Can create separate PRD if needed after initial investigation completes.

## Implementation Notes

### Phased Approach

**Phase 1: Core Utility**
1. Create `utils/performance.py` with timer context manager
2. Add unit tests or usage examples in docstrings

**Phase 2: Search Pipeline Integration**
1. Add timing to `search_tools.py` for main operations
2. Add timing to `context_retrieval.py` for context modes
3. Add JSON summary logging

**Phase 3: Validation**
1. Run test queries and verify log output
2. Verify timing measurements are reasonable (non-zero, not negative)
3. Verify JSON is valid and parseable

### Testing Strategy

Manual testing approach:
1. Start MCP server with instrumented code
2. Execute 3-5 search queries with different parameters:
   - Small query, `chunk_only` mode
   - Large query, `enhanced` mode
   - Large query, `full_note` mode
3. Examine logs at `/Users/michele/Library/Logs/Claude/`
4. Verify all timing markers appear
5. Verify JSON summary is valid
6. Parse JSON summaries and identify slowest operation

---

## Appendix: Key Operations to Instrument

Based on code analysis, these are the critical timing points:

### In `search_tools.py::search_knowledge_base()` (lines 47-143):
- **Total operation**: Wrap entire function (line 47-143)
- **ChromaDB client initialization**: Line 69
- **Collection validation**: Line 72
- **Query embedding generation**: Lines 86-87 (likely bottleneck #1)
- **ChromaDB query**: Lines 107-111 (likely bottleneck #2)
- **Result formatting**: Lines 114-128
- **Context retrieval**: Line 131 (likely bottleneck #3)

### In `context_retrieval.py`:
- **Enhanced context query**: Lines 32-41 (`get_enhanced_content`)
- **Full note query**: Lines 87-90 (`get_full_note_content`)

### Expected Timing Ranges (Hypothetical)
- **Query embedding**: 100-500ms (depends on Ollama/API latency)
- **ChromaDB search**: 10-100ms (depends on collection size)
- **Context retrieval (enhanced)**: 20-80ms (additional DB query)
- **Context retrieval (full_note)**: 50-200ms (potentially large query)
- **Total operation**: 200-800ms (sum of above + overhead)

These ranges will be validated once logging is implemented and real measurements are collected.
