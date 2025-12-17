# End-to-End Testing Guide for minerva-doc

This guide walks through comprehensive end-to-end testing of minerva-doc functionality.

## Prerequisites

1. **AI Provider**: Configure one of the following:
   - **Ollama** (recommended for local testing):
     ```bash
     ollama serve
     ollama pull mxbai-embed-large:latest
     ollama pull llama3.1:8b
     ```
   - **OpenAI**: Set `OPENAI_API_KEY` environment variable
   - **Gemini**: Set `GEMINI_API_KEY` environment variable
   - **LM Studio**: Start LM Studio server on `localhost:1234`

2. **Minerva Core**: Ensure minerva is installed:
   ```bash
   cd /Users/michele/my-code/minerva
   pip install -e .
   ```

3. **minerva-common**: Ensure shared library is installed:
   ```bash
   pip install -e tools/minerva-common
   ```

4. **minerva-doc**: Ensure minerva-doc is installed:
   ```bash
   pip install -e tools/minerva-doc
   ```

## Test Data

Test JSON files are located in `tools/minerva-doc/test-data/`:
- `sample-notes.json` - Original test data (3 notes)
- `sample-notes-updated.json` - Updated test data (4 notes)

## Test Suite 1: Basic Workflow

### Test 1.1: Add a Collection

```bash
cd /Users/michele/my-code/minerva/tools/minerva-doc

minerva-doc add test-data/sample-notes.json --name e2e-test
```

**Expected behavior:**
1. Validates JSON file ✓
2. Prompts for AI provider selection (choose one)
3. Prompts for collection description (or auto-generate)
4. Indexes collection
5. Displays success message

**Verify:**
```bash
# Check registry
cat ~/.minerva/apps/minerva-doc/collections.json | jq

# Should show e2e-test collection with metadata
```

### Test 1.2: List Collections

```bash
minerva-doc list
```

**Expected output:**
- Table format (default)
- Shows "e2e-test" under "Managed Collections"
- Displays: description, provider, chunk count, indexed date

**Also test JSON format:**
```bash
minerva-doc list --format json
```

**Verify:**
```bash
# Should output valid JSON with "managed" and "unmanaged" keys
minerva-doc list --format json | jq '.managed[].name'
```

### Test 1.3: Check Status

```bash
minerva-doc status e2e-test
```

**Expected output:**
- Collection name and description
- AI provider configuration
- ChromaDB status (chunk count)
- Dates (created, indexed)

### Test 1.4: Update Collection

```bash
minerva-doc update e2e-test test-data/sample-notes-updated.json
```

**Expected behavior:**
1. Validates new JSON file ✓
2. Shows current AI provider
3. Prompts: "Change AI provider? [y/N]"
   - Test both paths:
     - **N**: Uses existing provider and description
     - **Y**: Prompts for new provider and description

**Verify after update:**
```bash
minerva-doc status e2e-test
# Should show updated indexed_at timestamp
```

### Test 1.5: Remove Collection

```bash
minerva-doc remove e2e-test
```

**Expected behavior:**
1. Displays collection info
2. Shows warning about deletion
3. Prompts: "Type 'YES' to confirm removal"
4. Removes from ChromaDB
5. Removes from registry

**Verify:**
```bash
minerva-doc list
# Should NOT show e2e-test

cat ~/.minerva/apps/minerva-doc/collections.json | jq
# Should not contain e2e-test
```

## Test Suite 2: Error Handling

### Test 2.1: Invalid JSON File

```bash
minerva-doc add /nonexistent/file.json --name test
```

**Expected:** Error message about file not existing

### Test 2.2: Collection Already Exists

```bash
# First create a collection
minerva-doc add test-data/sample-notes.json --name duplicate-test

# Try to create again with same name
minerva-doc add test-data/sample-notes.json --name duplicate-test
```

**Expected:** Error about collision with helpful suggestions

**Cleanup:**
```bash
echo "YES" | minerva-doc remove duplicate-test
```

### Test 2.3: Update Non-Existent Collection

```bash
minerva-doc update nonexistent test-data/sample-notes.json
```

**Expected:** Error with helpful actions (list, add)

### Test 2.4: Status of Non-Existent Collection

```bash
minerva-doc status nonexistent
```

**Expected:** Error with helpful actions

### Test 2.5: Remove Non-Existent Collection

```bash
minerva-doc remove nonexistent
```

**Expected:** Error message

## Test Suite 3: Cross-Tool Integration

**Note:** These tests require minerva-kb to be installed.

### Test 3.1: Collision Prevention

```bash
# Create a collection with minerva-kb (if available)
minerva-kb add ~/code/some-repo

# Try to create minerva-doc collection with same name
minerva-doc add test-data/sample-notes.json --name some-repo-kb
```

**Expected:** Error message indicating collection exists, owned by minerva-kb

### Test 3.2: Cross-Tool Visibility

```bash
# With both minerva-kb and minerva-doc collections
minerva-doc list
```

**Expected:**
- "Managed Collections (minerva-doc)" section shows minerva-doc collections
- "Unmanaged Collections" section shows minerva-kb collections

### Test 3.3: Shared Server

```bash
# Create collections with both tools
minerva-doc add test-data/sample-notes.json --name doc-test
minerva-kb add ~/code/some-repo  # if available

# Start server (kills automatically after a few seconds for testing)
timeout 5s minerva-doc serve || true
```

**Expected:**
- Server starts successfully
- Both tools can serve the same server
- All collections in ChromaDB are accessible

## Test Suite 4: Validation

### Test 4.1: Valid JSON Schema

```bash
# Manually validate test data
minerva validate tools/minerva-doc/test-data/sample-notes.json
```

**Expected:** Validation passes

### Test 4.2: Invalid JSON Schema

Create invalid test file:
```bash
cat > /tmp/invalid.json << 'EOF'
[
  {
    "title": "Missing required fields"
  }
]
EOF

minerva-doc add /tmp/invalid.json --name invalid-test
```

**Expected:** Validation error with details about missing fields

**Cleanup:**
```bash
rm /tmp/invalid.json
```

## Test Suite 5: Provider Selection

### Test 5.1: Ollama Provider (Local)

```bash
# Ensure Ollama is running
curl http://localhost:11434/api/tags

minerva-doc add test-data/sample-notes.json --name ollama-test
# Select: Ollama
# Models: mxbai-embed-large:latest, llama3.1:8b
```

**Cleanup:**
```bash
echo "YES" | minerva-doc remove ollama-test
```

### Test 5.2: OpenAI Provider (Cloud)

```bash
# Set API key
export OPENAI_API_KEY="sk-your-key"

minerva-doc add test-data/sample-notes.json --name openai-test
# Select: OpenAI
# Models: text-embedding-3-small, gpt-4o-mini
```

**Cleanup:**
```bash
echo "YES" | minerva-doc remove openai-test
```

### Test 5.3: Provider Change on Update

```bash
# Create with Ollama
minerva-doc add test-data/sample-notes.json --name provider-test

# Update and change to OpenAI
minerva-doc update provider-test test-data/sample-notes-updated.json
# Answer Y to "Change AI provider?"
# Select: OpenAI
```

**Verify:**
```bash
minerva-doc status provider-test
# Should show OpenAI as provider
```

**Cleanup:**
```bash
echo "YES" | minerva-doc remove provider-test
```

## Test Results Tracking

### Task 2.12 Checklist

- [x] Test data created (sample-notes.json, sample-notes-updated.json)
- [ ] Test 1.1: Add collection (requires user interaction)
- [ ] Test 1.2: List collections (requires collection to exist)
- [ ] Test 1.3: Check status (requires collection to exist)
- [ ] Test 1.4: Update collection (requires user interaction)
- [ ] Test 1.5: Remove collection (requires user interaction)
- [ ] Test 2.x: Error handling (can be automated)
- [ ] Test 3.x: Cross-tool integration (requires minerva-kb)
- [ ] Test 4.x: Validation (partially automated)
- [ ] Test 5.x: Provider selection (requires user interaction/API keys)

## Notes

- **Interactive tests** require user input for provider selection and descriptions
- **Automated tests** can be scripted but require AI provider availability
- **Integration tests** require both minerva-kb and minerva-doc installed
- All tests should clean up after themselves (remove created collections)

## Quick Smoke Test

For a quick verification that everything works:

```bash
cd /Users/michele/my-code/minerva/tools/minerva-doc

# 1. Add
minerva-doc add test-data/sample-notes.json --name smoke-test
# Follow prompts, select Ollama if available

# 2. List
minerva-doc list

# 3. Status
minerva-doc status smoke-test

# 4. Update (answer N to provider change)
minerva-doc update smoke-test test-data/sample-notes-updated.json

# 5. Remove
echo "YES" | minerva-doc remove smoke-test

# Verify clean state
minerva-doc list
```

**Expected:** All commands succeed without errors.
