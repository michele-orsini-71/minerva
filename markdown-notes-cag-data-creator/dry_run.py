import sys
from storage import collection_exists, initialize_chromadb_client  # New immutable API

def calculate_dry_run_estimates(notes, config):
    """Calculate rough estimates for dry-run mode without actual chunking."""
    total_chars = sum(len(note['markdown']) for note in notes)
    avg_note_size = total_chars / len(notes) if notes else 0

    # Rough estimate: assume each chunk is target_chars size
    estimated_chunks = total_chars // config.chunk_size
    # Account for overlap and header boundaries (roughly +20% chunks)
    estimated_chunks = int(estimated_chunks * 1.2)

    # Estimate: ~4 bytes per dimension for embeddings (1024 dimensions typical)
    estimated_embedding_size = estimated_chunks * 1024 * 4 / (1024 * 1024)  # MB
    estimated_metadata_size = estimated_chunks * 0.001  # Rough estimate: 1KB per chunk metadata
    total_estimated_size = estimated_embedding_size + estimated_metadata_size

    return {
        'total_chars': total_chars,
        'avg_note_size': avg_note_size,
        'estimated_chunks': estimated_chunks,
        'total_estimated_size': total_estimated_size
    }


def print_dry_run_summary(config, notes, estimates, exists):
    """Print comprehensive dry-run summary."""
    print(f"Collection Configuration:")
    print(f"   Name: {config.collection_name}")
    print(f"   Description: {config.description}")
    print(f"   Force Recreate: {config.force_recreate}")
    print()
    print(f"Data Analysis:")
    print(f"   Source file: {config.json_file}")
    print(f"   Notes loaded: {len(notes)}")
    print(f"   Total content: {estimates['total_chars']:,} characters")
    print(f"   Average note size: {estimates['avg_note_size']:.0f} characters")
    print(f"   Target chunk size: {config.chunk_size} characters")
    print()
    print(f"Estimates (without actual chunking):")
    print(f"   Estimated chunks: ~{estimates['estimated_chunks']:,}")
    print(f"   Estimated storage: ~{estimates['total_estimated_size']:.2f} MB")
    print(f"   Note: Actual values may vary by ±20% depending on content structure")
    print()
    print(f"Collection Status:")
    print(f"   ChromaDB path: {config.chromadb_path}")
    print(f"   Collection exists: {'YES' if exists else 'NO'}")


def validate_dry_run_config(config, exists):
    """Validate configuration in dry-run mode and exit if invalid."""
    if exists and config.force_recreate:
        print(f"   Action: Will DELETE and recreate (WARNING: destructive!)")
    elif exists and not config.force_recreate:
        print(f"   Action: Will FAIL (collection exists, forceRecreate=false)")
        print(f"   ERROR: Configuration would fail in real run!")
        print(f"   Fix: Set 'forceRecreate': true or use different collection name")
        print()
        print("=" * 60)
        print("DRY-RUN VALIDATION FAILED")
        sys.exit(1)
    else:
        print(f"   Action: Will create new collection")


def run_dry_run_mode(config, args, notes):
    """Execute dry-run validation mode."""
    print("DRY-RUN PREVIEW (fast validation mode)")
    print("=" * 60)

    # Check if collection exists
    client = initialize_chromadb_client(config.chromadb_path)
    exists = collection_exists(client, config.collection_name)

    # Calculate estimates
    estimates = calculate_dry_run_estimates(notes, config)

    # Print summary
    print_dry_run_summary(config, notes, estimates, exists)

    # Validate and potentially exit
    validate_dry_run_config(config, exists)

    print()
    print("=" * 60)
    print("DRY-RUN VALIDATION SUCCESSFUL")
    print("Configuration is valid and ready for processing")
    print(f"Run without --dry-run to execute the pipeline")
    sys.exit(0)
