# Testing Guide for Multi-Collection MCP Server

This guide covers how to run tests, set up test data, and manually test the MCP server with Claude Desktop.

## Table of Contents

- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Setting Up Test Data](#setting-up-test-data)
- [Manual Testing with Claude Desktop](#manual-testing-with-claude-desktop)
- [Troubleshooting Test Failures](#troubleshooting-test-failures)

## Quick Start

```bash
# Activate virtual environment
source ../.venv/bin/activate

# Run all tests
pytest markdown-notes-mcp-server/tests/

# Run with verbose output
pytest -v markdown-notes-mcp-server/tests/

# Run specific test file
pytest markdown-notes-mcp-server/tests/test_integration.py
```

## Running Tests

### Running All Tests

From the repository root:

```bash
pytest markdown-notes-mcp-server/tests/
```

From the `markdown-notes-mcp-server/` directory:

```bash
pytest tests/
```

### Running Specific Test Suites

```bash
# Unit tests only (fast)
pytest tests/test_config.py tests/test_collection_discovery.py tests/test_search_tools.py tests/test_context_retrieval.py tests/test_startup_validation.py

# Integration tests only (slower, more comprehensive)
pytest tests/test_integration.py

# Specific test class
pytest tests/test_integration.py::TestCompleteFlow

# Specific test method
pytest tests/test_integration.py::TestCompleteFlow::test_full_workflow_list_then_search
```

### Useful pytest Options

```bash
# Verbose output (shows test names)
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate coverage report
pytest --cov=. --cov-report=html tests/
```

## Test Structure

### Test Organization

```
tests/
├── __init__.py                      # Makes tests a package
├── conftest.py                      # Shared fixtures (collections, embeddings, chunks)
├── test_config.py                   # Configuration loading and validation
├── test_collection_discovery.py    # Collection listing functionality
├── test_search_tools.py             # Semantic search implementation
├── test_context_retrieval.py        # Context mode logic (chunk_only, enhanced, full_note)
├── test_startup_validation.py       # Server initialization checks
└── test_integration.py              # End-to-end workflows and error scenarios
```

### Test Categories

#### Unit Tests (Fast, Isolated)

- **`test_config.py`**: Tests configuration file parsing, validation, and error messages
- **`test_collection_discovery.py`**: Tests ChromaDB collection listing with mocked client
- **`test_search_tools.py`**: Tests semantic search logic with mocked embeddings
- **`test_context_retrieval.py`**: Tests all three context modes with edge cases
- **`test_startup_validation.py`**: Tests server prerequisite checks (ChromaDB, Ollama, models)

#### Integration Tests (Slower, End-to-End)

- **`test_integration.py`**: Tests complete workflows:
  - List collections → search → retrieve context
  - All three context modes in realistic scenarios
  - Error handling across module boundaries
  - Configuration loading → validation → server initialization

### Shared Fixtures (`conftest.py`)

The `conftest.py` file provides reusable test fixtures:

- **`sample_embedding`**: Single normalized 1024-dim embedding vector
- **`sample_embeddings`**: Multiple embeddings for batch operations
- **`mock_chromadb_client`**: Mocked ChromaDB client with collections
- **`sample_chunks`**: Realistic chunk data with metadata
- **`mock_collection_with_search_results`**: Pre-configured collection for search tests
- **`sample_config`**: Valid configuration dictionary
- **`sample_search_results`**: Formatted search results for comparison

## Setting Up Test Data

### Using Mocked Data (Default)

All tests use mocked ChromaDB clients and embeddings by default. No real ChromaDB database or Ollama service required for unit tests.

```python
def test_example(mock_chromadb_client, sample_embedding):
    # Fixtures automatically provide mocked data
    collection = mock_chromadb_client.get_collection("bear_notes")
    # Test your code...
```

### Using Real ChromaDB Data (Optional)

For integration testing with real data:

1. **Create a test ChromaDB database:**

   ```bash
   cd ../bear-notes-cag-data-creator
   python full_pipeline.py \
       --collection-name "test_collection" \
       --collection-description "Test collection for integration testing" \
       --chromadb-path ../test_chromadb_data \
       ../test-data/sample.json
   ```

2. **Write tests that use the real database:**

   ```python
   import pytest
   from pathlib import Path

   @pytest.mark.skipif(
       not Path("../test_chromadb_data").exists(),
       reason="Real ChromaDB test data not available"
   )
   def test_with_real_chromadb():
       from collection_discovery import list_collections
       collections = list_collections("../test_chromadb_data")
       assert len(collections) > 0
   ```

3. **Run tests with real data:**

   ```bash
   pytest tests/test_integration.py -v
   ```

### Creating Custom Test Fixtures

Add custom fixtures to `conftest.py`:

```python
@pytest.fixture
def my_custom_collection():
    """Create a custom collection for specific test scenarios."""
    collection = Mock()
    collection.name = "my_test_collection"
    collection.metadata = {
        "description": "Custom test collection",
        "created_at": "2025-10-05T12:00:00Z",
        "version": "1.0"
    }
    collection.count.return_value = 10
    return collection
```

## Manual Testing with Claude Desktop

### Setup

1. **Ensure prerequisites are running:**

   ```bash
   # Terminal 1: Start Ollama
   ollama serve

   # Terminal 2: Verify model availability
   ollama list | grep mxbai-embed-large
   # If not available: ollama pull mxbai-embed-large:latest
   ```

2. **Create a configuration file:**

   ```bash
   cd markdown-notes-mcp-server
   cp config.json.example config.json
   # Edit config.json with your absolute paths
   ```

   Example `config.json`:

   ```json
   {
     "chromadb_path": "/Users/yourusername/path/to/search-markdown-notes/chromadb_data",
     "default_max_results": 3,
     "embedding_model": "mxbai-embed-large:latest"
   }
   ```

3. **Test server startup locally:**

   ```bash
   python server.py
   ```

   You should see:
   ```
   Server initialized successfully
   ChromaDB path: /path/to/chromadb_data
   Found 2 collections
   Ollama service: Available
   Model 'mxbai-embed-large:latest': Available

   MCP server running in stdio mode...
   ```

   Press `Ctrl+C` to stop.

### Adding to Claude Desktop

1. **Find your Claude Desktop config file:**

   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the MCP server configuration:**

   ```json
   {
     "mcpServers": {
       "markdown-notes": {
         "command": "python",
         "args": [
           "/absolute/path/to/search-markdown-notes/markdown-notes-mcp-server/server.py"
         ]
       }
     }
   }
   ```

   **Important:**
   - Use **absolute paths**, not relative paths like `~/` or `../`
   - The server reads `config.json` from its own directory (no need to pass ChromaDB path as env var)

3. **Restart Claude Desktop completely:**

   - Quit Claude Desktop (not just close the window)
   - Reopen Claude Desktop
   - Wait for initialization (check status bar for MCP server connection)

### Testing MCP Tools

Try these prompts in Claude Desktop:

#### Test Collection Discovery

```
What knowledge bases do you have access to?
```

Expected behavior:
- Claude calls `list_knowledge_bases` tool
- Returns list of collections with descriptions and chunk counts

#### Test Semantic Search (Enhanced Mode)

```
Search my notes for "Python async patterns"
```

Expected behavior:
- Claude calls `list_knowledge_bases` first (to determine collection name)
- Claude calls `search_knowledge_base` with appropriate collection
- Returns results with surrounding context and `[MATCH START]`/`[MATCH END]` markers

#### Test Different Context Modes

```
Search my notes for "Python async" using chunk_only mode
```

```
Search my notes for "Python async" using full_note mode
```

Expected behavior:
- `chunk_only`: Returns just the matched chunk
- `enhanced`: Returns matched chunk plus ±2 surrounding chunks (default)
- `full_note`: Returns the complete note with match marker

### Debugging MCP Server Issues

#### Check Server Logs

Claude Desktop logs MCP server output. Find logs at:

- **macOS**: `~/Library/Logs/Claude/`
- **Linux**: `~/.config/Claude/logs/`
- **Windows**: `%APPDATA%\Claude\logs\`

Look for files like `mcp-server-markdown-notes.log`

#### Test Server in Stdio Mode

Run the server directly and send JSON-RPC requests:

```bash
python server.py
```

Then type (or paste) this JSON-RPC request:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

Press Enter twice. You should see a response listing available tools.

#### Common Issues

**Server doesn't appear in Claude Desktop:**
- Check that `claude_desktop_config.json` has valid JSON syntax
- Verify absolute paths (no `~` or relative paths)
- Check Claude Desktop logs for error messages
- Restart Claude Desktop completely

**"Ollama service unavailable" error:**
- Ensure `ollama serve` is running in a separate terminal
- Test: `ollama list` should show installed models
- If needed: `ollama pull mxbai-embed-large:latest`

**"Collection not found" error:**
- Run `list_knowledge_bases` first to see available collections
- Verify ChromaDB path in `config.json` points to valid database
- Check that collections exist: `ls <chromadb_path>/`

**"ChromaDB path does not exist" error:**
- Verify `chromadb_path` in `config.json` uses absolute path
- Check that path exists: `ls <chromadb_path>/`
- If needed, create collections using the pipeline

## Troubleshooting Test Failures

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'collection_discovery'`

**Solution:**
```bash
# Tests modify sys.path to import parent modules
# Run pytest from repository root or markdown-notes-mcp-server/
pytest markdown-notes-mcp-server/tests/
```

### Mock-Related Failures

**Error:** `AttributeError: Mock object has no attribute 'some_method'`

**Solution:** Check that mocks are configured before being used:

```python
mock_collection.count.return_value = 150  # Configure BEFORE using
result = mock_collection.count()  # Now works
```

### Fixture Not Found

**Error:** `fixture 'sample_embedding' not found`

**Solution:** Ensure `conftest.py` is in the `tests/` directory and defines the fixture:

```bash
# Check fixture is defined
grep -n "def sample_embedding" tests/conftest.py
```

### Assertion Failures

**Error:** `AssertionError: assert 'expected text' in 'actual text'`

**Solution:** Use pytest's `-vv` flag to see full assertion details:

```bash
pytest -vv tests/test_integration.py::TestErrorScenarios::test_search_collection_not_found
```

### Tests Pass Individually but Fail in Suite

**Cause:** Shared state between tests (mocks not reset)

**Solution:** Use fresh fixtures for each test:

```python
@pytest.fixture
def mock_client():
    """Create fresh mock for each test."""
    return Mock()  # New instance per test
```

Or use `autouse` fixtures to reset state:

```python
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    yield
    # Cleanup code here
```

### Slow Integration Tests

**Cause:** Tests using real ChromaDB or Ollama

**Solution:** Mark slow tests and skip them:

```python
@pytest.mark.slow
def test_with_real_chromadb():
    # Slow test code...

# Run fast tests only:
# pytest -m "not slow"

# Run all tests including slow ones:
# pytest
```

## Test Coverage

Generate a coverage report to identify untested code:

```bash
# Install coverage tool
pip install pytest-cov

# Run tests with coverage
pytest --cov=. --cov-report=html tests/

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

Target coverage goals:
- **Unit tests**: >90% coverage of individual modules
- **Integration tests**: >80% coverage of workflows
- **Critical paths**: 100% coverage (error handling, validation)

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test MCP Server

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=. --cov-report=xml markdown-notes-mcp-server/tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices

1. **Write tests before code (TDD)**: Define expected behavior first
2. **Use descriptive test names**: `test_search_with_empty_query_raises_error`
3. **One assertion per test**: Easier to identify failures
4. **Mock external dependencies**: ChromaDB, Ollama, filesystem
5. **Test error cases**: Verify error messages are actionable
6. **Use fixtures for shared setup**: Avoid code duplication
7. **Keep tests fast**: Mock slow operations (embeddings, database queries)
8. **Document test intent**: Add docstrings explaining what's being tested

## Further Reading

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [FastMCP testing guide](https://github.com/jlowin/fastmcp#testing)
- [ChromaDB testing guide](https://docs.trychroma.com/guides#testing)
