import time
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from minerva.common.exceptions import IncrementalUpdateError
from minerva.common.logger import get_logger
from minerva.common.models import Chunk, ChunkList
from minerva.common.ai_provider import AIProvider
from minerva.indexing.chunking import generate_note_id, compute_content_hash, build_chunks_from_note
from minerva.indexing.embeddings import generate_embeddings
from minerva.indexing.storage import insert_chunks

logger = get_logger(__name__, mode="cli")

try:
    import chromadb
except ImportError as error:
    message = "chromadb library not installed"
    logger.error(f"{message}. Run: pip install chromadb")
    raise IncrementalUpdateError(message) from error


@dataclass
class UpdateStats:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0

    def total_changes(self) -> int:
        return self.added + self.updated + self.deleted

    def total_processed(self) -> int:
        return self.added + self.updated + self.deleted + self.unchanged


@dataclass
class ExistingState:
    noteId_to_chunks: Dict[str, List[Dict[str, Any]]]
    noteId_to_hash: Dict[str, str]


def is_v1_collection(collection: chromadb.Collection) -> bool:
    metadata = collection.metadata or {}
    version = metadata.get('version')
    return version is None or version == ""


@dataclass
class ConfigChange:
    has_changes: bool
    changed_fields: List[str]
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)


def detect_config_changes(
    collection: chromadb.Collection,
    current_embedding_model: str,
    current_embedding_provider: str,
    current_chunk_size: int
) -> ConfigChange:
    metadata = collection.metadata or {}

    stored_embedding_model = metadata.get('embedding_model')
    stored_embedding_provider = metadata.get('embedding_provider')
    stored_chunk_size = metadata.get('chunk_size')

    changed_fields = []
    old_values = {}
    new_values = {}

    if stored_embedding_model and stored_embedding_model != current_embedding_model:
        changed_fields.append('embedding_model')
        old_values['embedding_model'] = stored_embedding_model
        new_values['embedding_model'] = current_embedding_model

    if stored_embedding_provider and stored_embedding_provider != current_embedding_provider:
        changed_fields.append('embedding_provider')
        old_values['embedding_provider'] = stored_embedding_provider
        new_values['embedding_provider'] = current_embedding_provider

    if stored_chunk_size and stored_chunk_size != current_chunk_size:
        changed_fields.append('chunk_size')
        old_values['chunk_size'] = stored_chunk_size
        new_values['chunk_size'] = current_chunk_size

    has_changes = len(changed_fields) > 0

    return ConfigChange(
        has_changes=has_changes,
        changed_fields=changed_fields,
        old_values=old_values,
        new_values=new_values
    )


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
    current_metadata = collection.metadata or {}
    old_description = current_metadata.get('description')
    old_note_count = current_metadata.get('note_count')

    description_changed = old_description != new_description
    note_count_changed = old_note_count != new_note_count

    has_changes = description_changed or note_count_changed

    return MetadataChanges(
        has_changes=has_changes,
        description_changed=description_changed,
        note_count_changed=note_count_changed,
        old_description=old_description,
        new_description=new_description,
        old_note_count=old_note_count,
        new_note_count=new_note_count
    )


def format_v1_collection_error(collection_name: str, chromadb_path: str) -> str:
    return (
        f"\n"
        f"{'=' * 60}\n"
        f"Collection '{collection_name}' is v1.0 (legacy)\n"
        f"{'=' * 60}\n"
        f"\n"
        f"This collection was created with Minerva v1.0 and does not support\n"
        f"incremental updates. To use this collection, you must recreate it.\n"
        f"\n"
        f"Options:\n"
        f"  1. Add 'forceRecreate': true to your config\n"
        f"     (WARNING: This will permanently delete all existing data!)\n"
        f"  2. Use a different collection name\n"
        f"\n"
        f"Backup recommendation: Copy {chromadb_path} to a safe location\n"
        f"before upgrading.\n"
    )


def format_config_change_error(collection_name: str, config_change: ConfigChange) -> str:
    changes_detail = []

    if 'embedding_model' in config_change.changed_fields:
        old_val = config_change.old_values['embedding_model']
        new_val = config_change.new_values['embedding_model']
        changes_detail.append(f"  - Embedding model: {old_val} → {new_val}")

    if 'embedding_provider' in config_change.changed_fields:
        old_val = config_change.old_values['embedding_provider']
        new_val = config_change.new_values['embedding_provider']
        changes_detail.append(f"  - Provider: {old_val} → {new_val}")

    if 'chunk_size' in config_change.changed_fields:
        old_val = config_change.old_values['chunk_size']
        new_val = config_change.new_values['chunk_size']
        changes_detail.append(f"  - Chunk size: {old_val} → {new_val}")

    changes_text = "\n".join(changes_detail)

    return (
        f"\n"
        f"{'=' * 60}\n"
        f"Critical configuration change detected\n"
        f"{'=' * 60}\n"
        f"\n"
        f"The following settings have changed since collection '{collection_name}'\n"
        f"was created:\n"
        f"{changes_text}\n"
        f"\n"
        f"Incremental update is not possible because embeddings are incompatible.\n"
        f"\n"
        f"To reindex with new AI settings, set 'forceRecreate': true in your\n"
        f"configuration file.\n"
    )


def fetch_existing_state(collection: chromadb.Collection) -> ExistingState:
    logger.info("   Fetching existing chunks from ChromaDB...")

    total_count = collection.count()

    if total_count == 0:
        logger.info("   Collection is empty (no existing chunks)")
        return ExistingState(noteId_to_chunks={}, noteId_to_hash={})

    results = collection.get(
        include=["metadatas"]
    )

    noteId_to_chunks: Dict[str, List[Dict[str, Any]]] = {}
    noteId_to_hash: Dict[str, str] = {}

    if not results or not results.get("ids"):
        logger.warning("   No chunks retrieved from collection")
        return ExistingState(noteId_to_chunks={}, noteId_to_hash={})

    for i, chunk_id in enumerate(results["ids"]):
        metadata = results["metadatas"][i] if results.get("metadatas") else {}

        note_id = metadata.get("noteId")
        if not note_id:
            logger.warning(f"   Chunk {chunk_id} missing noteId metadata, skipping")
            continue

        chunk_data = {
            "id": chunk_id,
            "metadata": metadata
        }

        if note_id not in noteId_to_chunks:
            noteId_to_chunks[note_id] = []
        noteId_to_chunks[note_id].append(chunk_data)

        if metadata.get("chunkIndex") == 0 and "content_hash" in metadata:
            noteId_to_hash[note_id] = metadata["content_hash"]

    logger.success(f"   ✓ Fetched {len(results['ids'])} chunks from {len(noteId_to_chunks)} notes")

    return ExistingState(
        noteId_to_chunks=noteId_to_chunks,
        noteId_to_hash=noteId_to_hash
    )


@dataclass
class ChangeDetectionResult:
    added_notes: List[Dict[str, Any]]
    updated_notes: List[Dict[str, Any]]
    deleted_note_ids: List[str]
    unchanged_note_ids: List[str]


def detect_changes(
    new_notes: List[Dict[str, Any]],
    existing_state: ExistingState
) -> ChangeDetectionResult:
    logger.info("   Detecting changes between new and existing notes...")

    new_noteId_to_note: Dict[str, Dict[str, Any]] = {}
    new_noteId_to_hash: Dict[str, str] = {}

    for note in new_notes:
        note_id = generate_note_id(note['title'], note.get('creationDate'))
        content_hash = compute_content_hash(note['title'], note['markdown'])

        new_noteId_to_note[note_id] = note
        new_noteId_to_hash[note_id] = content_hash

    existing_note_ids = set(existing_state.noteId_to_hash.keys())
    new_note_ids = set(new_noteId_to_hash.keys())

    added_note_ids = new_note_ids - existing_note_ids
    deleted_note_ids = existing_note_ids - new_note_ids
    potentially_modified = new_note_ids & existing_note_ids

    added_notes = [new_noteId_to_note[nid] for nid in added_note_ids]
    updated_notes = []
    unchanged_note_ids = []

    for note_id in potentially_modified:
        new_hash = new_noteId_to_hash[note_id]
        existing_hash = existing_state.noteId_to_hash.get(note_id)

        if existing_hash is None:
            logger.warning(f"   Note {note_id} exists but missing content_hash, treating as updated")
            updated_notes.append(new_noteId_to_note[note_id])
        elif new_hash != existing_hash:
            updated_notes.append(new_noteId_to_note[note_id])
        else:
            unchanged_note_ids.append(note_id)

    logger.success(
        f"   ✓ Content changes detected: "
        f"{len(added_notes)} added, {len(updated_notes)} updated, "
        f"{len(deleted_note_ids)} deleted, {len(unchanged_note_ids)} unchanged"
    )

    return ChangeDetectionResult(
        added_notes=added_notes,
        updated_notes=updated_notes,
        deleted_note_ids=list(deleted_note_ids),
        unchanged_note_ids=unchanged_note_ids
    )


def delete_note_chunks(
    collection: chromadb.Collection,
    note_ids_to_delete: List[str],
    existing_state: ExistingState
) -> int:
    if not note_ids_to_delete:
        return 0

    logger.info(f"   Deleting chunks for {len(note_ids_to_delete)} removed notes...")

    chunk_ids_to_delete = []
    for note_id in note_ids_to_delete:
        chunks = existing_state.noteId_to_chunks.get(note_id, [])
        for chunk in chunks:
            chunk_ids_to_delete.append(chunk["id"])

    if not chunk_ids_to_delete:
        logger.warning("   No chunks found to delete")
        return 0

    try:
        collection.delete(ids=chunk_ids_to_delete)
        logger.success(f"   ✓ Deleted {len(chunk_ids_to_delete)} chunks")
        return len(chunk_ids_to_delete)
    except Exception as error:
        logger.error(f"   Failed to delete chunks: {error}")
        raise


def update_note_chunks(
    collection: chromadb.Collection,
    notes_to_update: List[Dict[str, Any]],
    existing_state: ExistingState,
    provider: AIProvider,
    target_chars: int,
    overlap_chars: int
) -> int:
    if not notes_to_update:
        return 0

    logger.info(f"   Updating chunks for {len(notes_to_update)} modified notes...")

    note_ids_to_delete = []
    for note in notes_to_update:
        note_id = generate_note_id(note['title'], note.get('creationDate'))
        note_ids_to_delete.append(note_id)

    delete_note_chunks(collection, note_ids_to_delete, existing_state)

    all_new_chunks = []
    for note in notes_to_update:
        chunks = build_chunks_from_note(note, target_chars, overlap_chars)
        all_new_chunks.extend(chunks)

    if not all_new_chunks:
        logger.warning("   No new chunks created during update")
        return 0

    chunks_with_embeddings = generate_embeddings(provider, all_new_chunks)

    insert_chunks(collection, chunks_with_embeddings)

    logger.success(f"   ✓ Updated {len(all_new_chunks)} chunks for {len(notes_to_update)} notes")
    return len(all_new_chunks)


def add_note_chunks(
    collection: chromadb.Collection,
    notes_to_add: List[Dict[str, Any]],
    provider: AIProvider,
    target_chars: int,
    overlap_chars: int
) -> int:
    if not notes_to_add:
        return 0

    logger.info(f"   Adding chunks for {len(notes_to_add)} new notes...")

    all_new_chunks = []
    for note in notes_to_add:
        chunks = build_chunks_from_note(note, target_chars, overlap_chars)
        all_new_chunks.extend(chunks)

    if not all_new_chunks:
        logger.warning("   No chunks created for new notes")
        return 0

    chunks_with_embeddings = generate_embeddings(provider, all_new_chunks)

    insert_chunks(collection, chunks_with_embeddings)

    logger.success(f"   ✓ Added {len(all_new_chunks)} chunks for {len(notes_to_add)} notes")
    return len(all_new_chunks)


def log_content_changes(changes: ChangeDetectionResult) -> None:
    """Log summary of content changes."""
    total_changes = len(changes.added_notes) + len(changes.updated_notes) + len(changes.deleted_note_ids)

    if total_changes == 0:
        logger.info("   ℹ No content changes detected")
    else:
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


def update_collection_metadata(
    collection: chromadb.Collection,
    metadata_changes: MetadataChanges
) -> None:
    """Update collection metadata based on detected changes."""
    from datetime import datetime, timezone

    current_timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_metadata = collection.metadata or {}
        updated_metadata = dict(current_metadata)

        # Remove immutable ChromaDB fields that cannot be modified
        # hnsw:space is set at collection creation and cannot be changed
        updated_metadata.pop('hnsw:space', None)

        updated_metadata['last_updated'] = current_timestamp

        if metadata_changes.description_changed:
            updated_metadata['description'] = metadata_changes.new_description

        if metadata_changes.note_count_changed:
            updated_metadata['note_count'] = metadata_changes.new_note_count

        collection.modify(metadata=updated_metadata)

        logger.info(f"   Updated collection metadata:")
        logger.info(f"      • Timestamp: {current_timestamp}")
        if metadata_changes.description_changed:
            logger.info(f"      • Description updated")
        if metadata_changes.note_count_changed:
            logger.info(f"      • Note count: {metadata_changes.old_note_count} → {metadata_changes.new_note_count}")
    except Exception as error:
        logger.warning(f"   Failed to update collection metadata: {error}")


def update_collection_timestamp(collection: chromadb.Collection, note_count: Optional[int] = None) -> None:
    from datetime import datetime, timezone

    current_timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_metadata = collection.metadata or {}
        updated_metadata = dict(current_metadata)

        # Remove immutable ChromaDB fields that cannot be modified
        # hnsw:space is set at collection creation and cannot be changed
        updated_metadata.pop('hnsw:space', None)

        updated_metadata['last_updated'] = current_timestamp

        # Update note_count if provided
        if note_count is not None:
            updated_metadata['note_count'] = note_count

        collection.modify(metadata=updated_metadata)

        logger.info(f"   Updated collection timestamp: {current_timestamp}")
        if note_count is not None:
            logger.info(f"   Updated note count: {note_count}")
    except Exception as error:
        logger.warning(f"   Failed to update collection timestamp: {error}")


def update_collection_description(
    collection: chromadb.Collection,
    new_description: str,
    note_count: Optional[int] = None
) -> None:
    from datetime import datetime, timezone

    current_timestamp = datetime.now(timezone.utc).isoformat()

    try:
        current_metadata = collection.metadata or {}
        updated_metadata = dict(current_metadata)

        # Remove immutable ChromaDB fields that cannot be modified
        # hnsw:space is set at collection creation and cannot be changed
        updated_metadata.pop('hnsw:space', None)

        updated_metadata['description'] = new_description
        updated_metadata['last_updated'] = current_timestamp

        # Update note_count if provided
        if note_count is not None:
            updated_metadata['note_count'] = note_count

        collection.modify(metadata=updated_metadata)

        logger.info(f"   Updated collection description")
        logger.info(f"   Updated collection timestamp: {current_timestamp}")
        if note_count is not None:
            logger.info(f"   Updated note count: {note_count}")
    except Exception as error:
        logger.warning(f"   Failed to update collection metadata: {error}")


def print_update_summary(stats: UpdateStats, elapsed_time: float, collection_name: str) -> None:
    logger.info("")
    logger.info("=" * 70)
    logger.info("Incremental update complete!")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Collection: {collection_name}")
    logger.info(f"Elapsed time: {elapsed_time:.2f} seconds")
    logger.info("")
    logger.info("Changes:")
    logger.success(f"  ✓ Added: {stats.added} notes")
    logger.success(f"  ✓ Updated: {stats.updated} notes")
    logger.success(f"  ✓ Deleted: {stats.deleted} notes")
    logger.info(f"  • Unchanged: {stats.unchanged} notes")
    logger.info("")
    logger.info(f"Total notes processed: {stats.total_processed()}")
    logger.info(f"Total changes: {stats.total_changes()}")
    logger.info("")

    if stats.total_changes() == 0:
        logger.info("ℹ No changes detected - collection is up to date")
    else:
        change_percentage = (stats.total_changes() / stats.total_processed() * 100) if stats.total_processed() > 0 else 0
        logger.info(f"ℹ Change rate: {change_percentage:.1f}% of notes modified")

    logger.info("=" * 70)


def run_incremental_update(
    collection: chromadb.Collection,
    new_notes: List[Dict[str, Any]],
    provider: AIProvider,
    new_description: str,
    target_chars: int = 1200,
    overlap_chars: int = 200
) -> UpdateStats:
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("Starting incremental update...")
    logger.info("=" * 70)

    stats = UpdateStats()

    existing_state = fetch_existing_state(collection)

    # 1. Detect content changes (notes)
    logger.info("")
    content_changes = detect_changes(new_notes, existing_state)

    # 2. Detect metadata changes (separate!)
    metadata_changes = detect_metadata_changes(
        collection,
        new_description=new_description,
        new_note_count=len(new_notes)
    )

    # 3. Log both types of changes
    logger.info("")
    log_content_changes(content_changes)
    log_metadata_changes(metadata_changes)
    logger.info("")

    # 4. Process content changes
    if content_changes.deleted_note_ids:
        delete_note_chunks(collection, content_changes.deleted_note_ids, existing_state)
        stats.deleted = len(content_changes.deleted_note_ids)

    if content_changes.updated_notes:
        update_note_chunks(
            collection,
            content_changes.updated_notes,
            existing_state,
            provider,
            target_chars,
            overlap_chars
        )
        stats.updated = len(content_changes.updated_notes)

    if content_changes.added_notes:
        add_note_chunks(
            collection,
            content_changes.added_notes,
            provider,
            target_chars,
            overlap_chars
        )
        stats.added = len(content_changes.added_notes)

    stats.unchanged = len(content_changes.unchanged_note_ids)

    # 5. Update metadata if changed
    logger.info("")
    if metadata_changes.has_changes:
        update_collection_metadata(collection, metadata_changes)
    else:
        update_collection_timestamp(collection)

    elapsed_time = time.time() - start_time
    print_update_summary(stats, elapsed_time, collection.name)

    return stats
