from minerva_kb.commands import run_add, run_sync


def test_sync_reindexes_collection(kb_env):
    repo = kb_env.create_repo("alpha")
    kb_env.queue_provider()
    run_add(str(repo))

    assert run_sync("alpha") == 0


def test_sync_handles_missing_collection(kb_env):
    assert run_sync("missing") == 1


def test_sync_reports_extraction_failure(kb_env):
    repo = kb_env.create_repo("bravo")
    kb_env.queue_provider()
    run_add(str(repo))
    kb_env.fail_extraction = True

    assert run_sync("bravo") == 2


def test_sync_reports_indexing_failure(kb_env):
    repo = kb_env.create_repo("charlie")
    kb_env.queue_provider()
    run_add(str(repo))
    kb_env.fail_indexing = True

    assert run_sync("charlie") == 3
