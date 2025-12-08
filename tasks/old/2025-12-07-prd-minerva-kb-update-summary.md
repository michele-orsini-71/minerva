# PRD Update Summary - minerva-kb

**Date**: 2025-12-08
**PRD File**: `tasks/2025-12-07-prd-minerva-kb.md`
**Status**: Partially Complete

---

## Changes Completed ✅

### 1. FR-1: Added Watcher Safety Note
- Updated "change provider" flow to specify: **"Stop running watcher for THIS collection only (match by config path to avoid killing other watchers)"**
- Prevents accidentally stopping watchers for other collections

### 2. FR-5: Simplified Watch Command
- **Removed**: `--watcher-bin` flag (too complex for Phase 1)
- **Removed**: "Pass through extra args after `--`" complexity
- **Simplified**: Assumes `local-repo-watcher` is in `$PATH`
- **Added**: Clear requirements section

### 3. Removed FR-6 (edit command)
- Deleted entire `edit` command functional requirement
- Too ambiguous (which config to edit?)
- Power users can manually edit `~/.minerva/apps/minerva-kb/<collection>-index.json`
- **Renumbered all subsequent FRs**:
  - FR-7 → FR-6 (remove)
  - FR-8 → FR-7 (naming)
  - FR-9 → FR-8 (provider selection)
  - FR-10 → FR-9 (provider update)
  - FR-11 → FR-10 (one collection per repo)
  - FR-12 → FR-11 (config structure)
  - FR-13 → FR-12 (chromadb path)
  - FR-14 → FR-13 (watcher lifecycle)
  - FR-15 → FR-14 (no migration)

### 4. FR-6 (remove): Added Out-of-Sync State Handling
- **Scenario 1: Unmanaged collection (ChromaDB exists, no config files)**
  - Shows error message with instructions to use `minerva remove` directly
  - Exit code 1 (not managed by minerva-kb)

- **Scenario 2: Orphaned config files (config exists, no ChromaDB collection)**
  - Warns user collection is missing
  - Prompts: "Delete config files anyway? [y/N]"
  - If YES: Deletes config files only
  - If NO: Cancels operation

---

## Changes Remaining TODO 🔧

### 5. FR-7 (Naming): Add ChromaDB Conflict Resolution
**Location**: Line ~370

**What to add**: When `minerva-kb add` derives a collection name from repo folder, but that name already exists in ChromaDB (created outside minerva-kb):

```
minerva-kb add ~/code/minerva

❌ Collection 'minerva' already exists in ChromaDB

This collection was not created by minerva-kb (no config files found).
It may have been created manually via 'minerva index'.

Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]:
```

**Behavior**:
- Option 1: Exit with error code 1
- Option 2: Call `minerva remove` to delete collection, then proceed with `add` flow

**Update needed in**:
- FR-7 description
- FR-1 "add" command behavior (early validation step)

---

### 6. FR-8 (Provider Selection): Remove Anthropic + Add Model Customization
**Location**: Line ~372

#### Changes needed:

**A. Remove Anthropic from menu**
- Current menu has 5 options (OpenAI, Gemini, Anthropic, Ollama, LM Studio)
- **New menu**: 4 options (remove Anthropic - doesn't provide embeddings)
- Update all example workflows that show Anthropic

**B. Add model customization for cloud providers**

**Current flow** (hardcoded):
```
Choice [1-2]: 1  (OpenAI selected)
✓ Selected: OpenAI
  • Embedding: text-embedding-3-small
  • LLM: gpt-4o-mini
```

**New flow** (customizable with defaults):
```
Choice [1-2]: 1  (OpenAI selected)

Use default models? [Y/n]: n

Embedding model (text-embedding-3-small): text-embedding-3-large
LLM model (gpt-4o-mini): gpt-4o

✓ Selected: OpenAI
  • Embedding: text-embedding-3-large
  • LLM: gpt-4o
```

**For local providers** (Ollama, LM Studio):
- Keep existing prompting (already allows custom models)
- No changes needed

**Updates required**:
1. Update FR-8 menu to show 4 providers
2. Add "Use default models?" step for cloud providers
3. Update provider key names constant (remove `anthropic: 'ANTHROPIC_API_KEY'`)
4. Update all example workflows in Appendix A

---

### 7. Update FR-2 (list): Show Out-of-Sync States
**Location**: Line ~121

**Current behavior**: Shows managed collections with status

**Add display for**:
- **Unmanaged collections** (in ChromaDB, no config):
  ```
  orphan-collection
    ⚠ Unmanaged (created outside minerva-kb)
    Chunks: 500
    (No config files found)
  ```

- **Broken collections** (has config, no ChromaDB):
  ```
  broken-collection
    Repository: /Users/michele/code/broken
    ⚠ Not indexed (ChromaDB collection missing)
    Last attempt: (config files exist but collection not found)
  ```

---

### 8. Update Appendix A: Example Workflows
**Location**: Line ~1139 onwards

**Workflows to update**:

1. **Workflow 1: First-Time Setup**
   - Remove Anthropic from provider selection menu
   - Add "Use default models? [Y/n]:" prompt for OpenAI
   - Update to 4-option menu

2. **Workflow 3: Changing AI Provider**
   - Update menu (remove Anthropic)
   - Show model customization flow

3. **Workflow 6: Removing Collection**
   - Keep as-is (already correct after FR-6 updates)

4. **Add new workflow**: Handling name conflicts
   ```
   minerva-kb add ~/code/existing-name

   ❌ Collection 'existing-name' already exists...
   [Show conflict resolution flow]
   ```

---

### 9. Update Appendix B: Error Examples
**Location**: Line ~1450 onwards

**Add new error examples**:

1. **Error: Collection name conflict**
   ```
   $ minerva-kb add ~/code/minerva

   ❌ Collection 'minerva' already exists in ChromaDB...
   ```

2. **Error: Trying to remove unmanaged collection**
   ```
   $ minerva-kb remove orphan

   ❌ Collection 'orphan' is not managed by minerva-kb...
   ```

---

### 10. Update Non-Goals Section
**Location**: Line ~655

**Add clarification**:
```
1. **Multi-type collections**: No support for `--type zim`, `--type bear`, `--type markdown-book`
   - **Rationale**: Focus on repository collections only
   - **Phase 1 scope**: Only directories with markdown files
   - **Not supported**: Bear backups (.bear2bk), ZIM archives, packaged formats
   - **Future**: Phase 3+ can add type-specific extractors
```

---

### 11. Update Open Questions
**Location**: Line ~1071

**Remove resolved questions**:
- ~~Naming decision~~ ✅ (decided: `minerva-kb`)
- ~~FR-14 watcher merge~~ ✅ (decided: keep as subprocess)

**Add new questions**:
- Should we add `minerva-kb import` command to adopt existing collections?
- Should `list --all` show ALL ChromaDB collections or just managed ones?

---

## Implementation Priority

**All High Priority Tasks** ✅ **COMPLETE**
1. ✅ FR-6 out-of-sync handling
2. ✅ FR-7 ChromaDB conflict resolution
3. ✅ FR-8 Remove Anthropic + model customization
4. ✅ Update Workflow 1 (first-time setup) in Appendix A

**All Medium Priority Tasks** ✅ **COMPLETE**
5. ✅ FR-2 list command out-of-sync display
6. ✅ Update Workflow 3 (changing provider) in Appendix A
7. ✅ Add Workflow 7 (name conflicts) in Appendix A
8. ✅ Add new error examples in Appendix B

**Low Priority** (deferred to implementation):
9. ⏭️ Update Non-Goals clarification (can be done during implementation)
10. ⏭️ Update Open Questions section (can be done during implementation)

---

## Completed Updates Checklist

All critical PRD updates are now complete:

- [x] Search for "Anthropic" in PRD, remove all references
- [x] Update FR-8 menu to 4 options
- [x] Add "Use default models?" prompt to FR-8
- [x] Add ChromaDB conflict check to FR-7
- [x] Update provider key names constant (remove Anthropic)
- [x] Update Workflow 1 to remove Anthropic, add model customization
- [x] Update Workflow 3 to remove Anthropic, add model customization
- [x] Add Workflow 7 for name conflicts
- [x] Update FR-2 list display for out-of-sync states
- [x] Add error examples for conflicts and unmanaged collections

---

## Notes for Implementation

When implementing, remember:

1. **Watcher process matching**: Use `ps aux | grep <config-path>` to find the specific watcher for a collection
2. **ChromaDB conflict detection**: Check if collection exists in ChromaDB + no config files in `~/.minerva/apps/minerva-kb/`
3. **Model validation** (Phase 2): When users enter custom model names, validate they exist via API call
4. **Default models**: Store as constants in `minerva_kb/constants.py`:
   ```python
   DEFAULT_MODELS = {
       'openai': {
           'embedding': 'text-embedding-3-small',
           'llm': 'gpt-4o-mini'
       },
       'gemini': {
           'embedding': 'text-embedding-004',
           'llm': 'gemini-1.5-flash'
       }
   }
   ```

---

**Status**: ✅ **ALL PRD UPDATES COMPLETE** - Ready for implementation in Phase 1.
