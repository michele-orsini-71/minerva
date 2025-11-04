Plan: Proper Metadata Change Detection for Incremental Updates

1. Create detect_metadata_changes() function in updater.py

Purpose: Explicitly track all non-critical metadata changes (fields that don't require full reindex)
Function signature:
@dataclass
class MetadataChanges:
    has_changes: bool
    description_changed: bool
    note_count_changed: bool
    old_description: Optional[str]
    new_description: str
    old_note_count: Optional[int]
    new_note_count: int
def detect_metadata_changes(
    collection: chromadb.Collection,
    new_description: str,
    new_note_count: int
) -> MetadataChanges:
    """Detect changes in collection metadata that don't require reindexing."""
Implementation:
- Read current metadata from collection
- Compare description: old != new
- Compare note_count: old != new
- Return structured result with old/new values for logging
Location: Add after detect_config_changes() (~line 95 in updater.py)
---
2. Update ChangeDetectionResult dataclass
Current:
@dataclass
class ChangeDetectionResult:
    added_notes: List[Dict[str, Any]]
    updated_notes: List[Dict[str, Any]]
    deleted_note_ids: List[str]
    unchanged_note_ids: List[str]
    description_changed: bool  # ← Remove this, move to MetadataChanges
New:
@dataclass
class ChangeDetectionResult:
    added_notes: List[Dict[str, Any]]
    updated_notes: List[Dict[str, Any]]
    deleted_note_ids: List[str]
    unchanged_note_ids: List[str]
    # description_changed removed - now in MetadataChanges
---
3. Refactor detect_changes() function
Changes:
- Remove current_description and new_description parameters
- Remove description_changed field from result (line 252, 260-261, 268)
- Focus purely on note content changes
- Simplify function signature
Before:
def detect_changes(
    new_notes: List[Dict[str, Any]],
    existing_state: ExistingState,
    current_description: Optional[str],  # ← Remove
    new_description: str  # ← Remove
) -> ChangeDetectionResult:
After:
def detect_changes(
    new_notes: List[Dict[str, Any]],
    existing_state: ExistingState
) -> ChangeDetectionResult:
---
4. Update run_incremental_update() function
Changes:
- Call detect_metadata_changes() separately from detect_changes()
- Update logging to show both content and metadata changes
- Refactor metadata update logic to use MetadataChanges result
New flow (~lines 447-508):
def run_incremental_update(...) -> UpdateStats:
    # ... existing setup ...
    existing_state = fetch_existing_state(collection)
    # 1. Detect content changes (notes)
    content_changes = detect_changes(new_notes, existing_state)
    # 2. Detect metadata changes (separate!)
    metadata_changes = detect_metadata_changes(
        collection,
        new_description=new_description,
        new_note_count=len(new_notes)
    )
    # 3. Log both types of changes
    log_content_changes(content_changes)
    log_metadata_changes(metadata_changes)
    # 4. Process content changes
    if content_changes.deleted_note_ids:
        delete_note_chunks(...)
    if content_changes.updated_notes:
        update_note_chunks(...)
    if content_changes.added_notes:
        add_note_chunks(...)
    # 5. Update metadata if changed
    if metadata_changes.has_changes:
        update_collection_metadata(collection, metadata_changes)
    else:
        update_collection_timestamp(collection)
---
5. Create unified metadata update function
Purpose: Single function to update all metadata fields consistently
New function:
def update_collection_metadata(
    collection: chromadb.Collection,
    metadata_changes: MetadataChanges
) -> None:
    """Update collection metadata based on detected changes."""
    current_timestamp = datetime.now(timezone.utc).isoformat()
    current_metadata = collection.metadata or {}
    updated_metadata = dict(current_metadata)
    updated_metadata['last_updated'] = current_timestamp
    if metadata_changes.description_changed:
        updated_metadata['description'] = metadata_changes.new_description
    if metadata_changes.note_count_changed:
        updated_metadata['note_count'] = metadata_changes.new_note_count
    collection.modify(metadata=updated_metadata)
    # Log what changed
    if metadata_changes.description_changed:
        logger.info(f"   Updated description")
    if metadata_changes.note_count_changed:
        logger.info(f"   Updated note count: {metadata_changes.old_note_count} → {metadata_changes.new_note_count}")
Decision: Keep or deprecate update_collection_description() and update_collection_timestamp()?
- Option A: Keep for backward compatibility, mark as deprecated
- Option B: Remove and use only update_collection_metadata()
- Recommendation: Option B (cleaner, single source of truth)
---
6. Add logging helpers
New functions:
def log_content_changes(changes: ChangeDetectionResult) -> None:
    """Log summary of content changes."""
    logger.success(
        f"   ✓ Content changes: "
        f"{len(changes.added_notes)} added, "
        f"{len(changes.updated_notes)} updated, "
        f"{len(changes.deleted_note_ids)} deleted, "
        f"{len(changes.unchanged_note_ids)} unchanged"
    )
def log_metadata_changes(changes: MetadataChanges) -> None:
    """Log summary of metadata changes."""
    if not changes.has_changes:
        logger.info("   ℹ No metadata changes detected")
        return
    logger.info("   ℹ Metadata changes detected:")
    if changes.description_changed:
        logger.info(f"      • Description changed")
    if changes.note_count_changed:
        logger.info(f"      • Note count: {changes.old_note_count} → {changes.new_note_count}")
---
7. Update run_incremental_indexing() in index.py
Changes:
- Pass correct parameters to run_incremental_update()
- Ensure new_notes list is available for note count calculation
Location: index.py:265-309
---
8. Testing considerations
What to test:
1. ✅ Content-only changes (add/update/delete notes)
2. ✅ Metadata-only changes (description or note_count change, no content)
3. ✅ Combined changes (both content and metadata)
4. ✅ No changes (timestamp-only update)
5. ✅ Critical field changes still block incremental update
---
Summary of Files to Modify
1. minerva/indexing/updater.py (primary changes)
  - Add MetadataChanges dataclass
  - Add detect_metadata_changes() function
  - Add update_collection_metadata() function
  - Add log_content_changes() and log_metadata_changes() helpers
  - Refactor detect_changes() - remove description logic
  - Refactor run_incremental_update() - use new functions
  - Update ChangeDetectionResult dataclass
  - Deprecate/remove update_collection_description()
2. minerva/commands/index.py (minor changes)
  - Update run_incremental_indexing() if needed
  - Ensure proper parameter passing
---
Benefits
✅ Clear separation of concerns: Content changes vs metadata changes✅ Explicit tracking: All metadata changes are detected and logged✅ Future-proof: Easy to add new metadata fields (e.g., schema_version, last_validated)✅ Better logging: Users see exactly
what changed✅ Maintainable: No more "side effect" updates✅ Testable: Each function has single responsibility
