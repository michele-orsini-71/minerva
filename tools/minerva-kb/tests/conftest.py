import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from minerva_common import collection_ops as common_collection_ops
from minerva_common import collision as common_collision
from minerva_common import init as common_init
from minerva_common import paths as common_paths
from minerva_kb import constants as constants_mod
from minerva_kb.commands import add as add_cmd
from minerva_kb.commands import list as list_cmd
from minerva_kb.commands import remove as remove_cmd
from minerva_kb.commands import status as status_cmd
from minerva_kb.commands import sync as sync_cmd
from minerva_kb.commands import watch as watch_cmd
from minerva_kb.commands import serve as serve_cmd
from minerva_kb.utils import config_helpers, config_loader, description_generator
from minerva_kb.utils.collection_naming import sanitize_collection_name


class FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self.documents: list[str] = []
        self.metadata: dict = {}

    def upsert(self, ids, documents):  # noqa: ARG002
        self.documents = list(documents)

    def count(self) -> int:
        return len(self.documents)


class FakePersistentClient:
    def __init__(self):
        self._collections: dict[str, FakeCollection] = {}

    def get_or_create_collection(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection(name)
        return self._collections[name]

    def get_collection(self, name: str) -> FakeCollection:
        if name not in self._collections:
            raise ValueError("Collection not found")
        return self._collections[name]

    def list_collections(self):
        return list(self._collections.values())

    def delete_collection(self, name: str) -> None:
        self._collections.pop(name, None)


class FakeSubprocessRunner:
    def __init__(self, env):
        self.env = env
        self.calls: list[list[str]] = []
        self.watcher_available = True

    def run(self, args, capture_output=False, text=False, timeout=None, check=False, input=None):
        command = list(args)
        self.calls.append(command)
        binary = command[0]

        if binary == "repository-doc-extractor":
            return self._handle_extractor(command)
        if binary == "minerva":
            return self._handle_minerva(command, input)
        if binary == "which" and command[1] == "local-repo-watcher":
            if not self.watcher_available:
                return SimpleNamespace(returncode=1, stdout="", stderr="not found")
            return SimpleNamespace(returncode=0, stdout="/usr/bin/local-repo-watcher\n", stderr="")
        if binary == "ps":
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        raise AssertionError(f"Unexpected subprocess command: {command}")

    def _handle_extractor(self, command):
        output_path = Path(command[-1]).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.env.fail_extraction:
            raise subprocess.CalledProcessError(returncode=2, cmd=command, output="extraction failed")
        output_path.write_text(json.dumps({"documents": []}))
        return SimpleNamespace(returncode=0, stdout="extracted", stderr="")

    def _handle_minerva(self, command, input_data):
        action = command[1]
        if action == "index":
            config_index = command.index("--config") + 1
            config_path = Path(command[config_index]).expanduser()
            if self.env.fail_indexing:
                raise subprocess.CalledProcessError(returncode=3, cmd=command, output="index failed")
            self._simulate_index(config_path)
            return SimpleNamespace(returncode=0, stdout="indexed", stderr="")
        if action == "remove":
            chroma_path = Path(command[2]).expanduser()
            collection_name = command[3]
            self._simulate_remove(chroma_path, collection_name)
            return SimpleNamespace(returncode=0, stdout="removed", stderr="")
        raise AssertionError(f"Unsupported minerva action: {command}")

    def _simulate_index(self, config_path: Path) -> None:
        payload = json.loads(config_path.read_text())
        collection = self.env.fake_client.get_or_create_collection(payload["collection"]["name"])
        collection.upsert(
            ids=["doc-1"],
            documents=[f"Indexed {payload['collection']['name']}"]
        )

    def _simulate_remove(self, chroma_path: Path, collection_name: str) -> None:
        self.env.fake_client.delete_collection(collection_name)


class FakeWatcherProcess:
    def __init__(self, env, args, **kwargs):  # noqa: ARG002
        self.env = env
        self.args = list(args)
        self.returncode = 0
        config_index = self.args.index("--config") + 1
        self.config_path = str(Path(self.args[config_index]).expanduser())
        self.env.running_watchers[self.config_path] = self.env.next_pid()

    def wait(self):
        self.env.running_watchers.pop(self.config_path, None)
        return self.returncode


class KBTestEnv:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        self.tmp_path = tmp_path
        self.monkeypatch = monkeypatch
        self.minerva_dir = tmp_path / ".minerva"
        self.app_dir = tmp_path / ".minerva" / "apps" / "minerva-kb"
        self.chroma_dir = tmp_path / ".minerva" / "chromadb"
        self.repos_dir = tmp_path / "repositories"
        self.server_config_path = tmp_path / ".minerva" / "server.json"
        self.minerva_dir.mkdir(parents=True, exist_ok=True)
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir()
        self.provider_queue: list[dict[str, str]] = []
        self.running_watchers: dict[str, int] = {}
        self.pid_counter = 3200
        self.fail_extraction = False
        self.fail_indexing = False
        self.subprocess_runner = FakeSubprocessRunner(self)
        self.fake_client = FakePersistentClient()

        self._patch_constants()
        self._patch_provider_selection()
        self._patch_process_helpers()
        self._patch_description_generator()
        self._patch_subprocesses()

    def _patch_constants(self) -> None:
        # Patch minerva_common.paths first
        apps_dir = self.minerva_dir / "apps"
        self.monkeypatch.setattr(common_paths, "MINERVA_DIR", self.minerva_dir)
        self.monkeypatch.setattr(common_paths, "CHROMADB_DIR", self.chroma_dir)
        self.monkeypatch.setattr(common_paths, "APPS_DIR", apps_dir)
        self.monkeypatch.setattr(common_paths, "SERVER_CONFIG_PATH", self.server_config_path)
        self.monkeypatch.setattr(common_init, "MINERVA_DIR", self.minerva_dir)
        self.monkeypatch.setattr(common_init, "CHROMADB_DIR", self.chroma_dir)
        self.monkeypatch.setattr(common_init, "SERVER_CONFIG_PATH", self.server_config_path)
        self.monkeypatch.setattr(common_collision, "APPS_DIR", apps_dir)
        self.monkeypatch.setattr(common_collision, "CHROMADB_DIR", self.chroma_dir)
        self.monkeypatch.setattr(
            common_collision,
            "get_collection_count",
            lambda chroma_path, name, self=self: self._collection_doc_count(name),
        )
        self.monkeypatch.setattr(
            common_collection_ops,
            "get_collection_count",
            lambda chroma_path, name, self=self: self._collection_doc_count(name),
        )

        # Patch minerva-kb modules
        modules = [
            constants_mod,
            config_loader,
            config_helpers,
            add_cmd,
            list_cmd,
            status_cmd,
            sync_cmd,
            watch_cmd,
            remove_cmd,
            serve_cmd,
        ]
        for module in modules:
            if hasattr(module, "MINERVA_KB_APP_DIR"):
                self.monkeypatch.setattr(module, "MINERVA_KB_APP_DIR", self.app_dir)
            if hasattr(module, "CHROMADB_DIR"):
                self.monkeypatch.setattr(module, "CHROMADB_DIR", self.chroma_dir)
            if hasattr(module, "PersistentClient"):
                self.monkeypatch.setattr(module, "PersistentClient", lambda *args, **kwargs: self.fake_client)

    def _patch_provider_selection(self) -> None:
        self.monkeypatch.setattr(add_cmd, "interactive_select_provider", self._select_provider)

    def _patch_process_helpers(self) -> None:
        for module in (add_cmd, list_cmd, status_cmd, watch_cmd, remove_cmd):
            self.monkeypatch.setattr(module, "find_watcher_pid", self._find_watcher_pid)
        for module in (add_cmd, remove_cmd):
            self.monkeypatch.setattr(module, "stop_watcher", self._stop_watcher)

    def _patch_description_generator(self) -> None:
        def fake_provider(prompt: str, provider_config: dict[str, str]) -> str:  # noqa: ARG001
            return "Generated description"

        self.monkeypatch.setattr(description_generator, "_call_provider", fake_provider)

    def _patch_subprocesses(self) -> None:
        for module in (add_cmd, sync_cmd, watch_cmd, remove_cmd):
            self.monkeypatch.setattr(module.subprocess, "run", self.subprocess_runner.run)
        self.monkeypatch.setattr(
            watch_cmd.subprocess,
            "Popen",
            lambda args, **kwargs: FakeWatcherProcess(self, args, **kwargs),
        )

    def _select_provider(self) -> dict[str, str]:
        if self.provider_queue:
            config = self.provider_queue.pop(0)
        else:
            config = self.default_provider()
        return dict(config)

    def _find_watcher_pid(self, config_path: Path | str) -> int | None:
        return self.running_watchers.get(str(config_path))

    def _stop_watcher(self, pid: int) -> bool:  # noqa: ARG002
        for path, stored_pid in list(self.running_watchers.items()):
            if stored_pid == pid:
                del self.running_watchers[path]
        return True

    def default_provider(self) -> dict[str, str]:
        return {
            "provider_type": "openai",
            "embedding_model": "text-embedding-3-small",
            "llm_model": "gpt-4o-mini",
            "api_key": "${OPENAI_API_KEY}",
        }

    def queue_provider(self, provider: dict[str, str] | None = None) -> None:
        self.provider_queue.append(provider or self.default_provider())

    def create_repo(self, name: str, *, with_readme: bool = True) -> Path:
        repo = self.repos_dir / name
        repo.mkdir()
        if with_readme:
            (repo / "README.md").write_text(f"# {name}\n")
        return repo

    def collection_name(self, repo: Path | str) -> str:
        return sanitize_collection_name(repo)

    def register_collection_owner(self, app_name: str, collection_name: str) -> None:
        registry_dir = self.minerva_dir / "apps" / app_name
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_path = registry_dir / "collections.json"
        if registry_path.exists():
            try:
                data = json.loads(registry_path.read_text() or "{}")
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
        collections = data.setdefault("collections", {})
        collections[collection_name] = {"name": collection_name}
        registry_path.write_text(json.dumps(data))

    def next_pid(self) -> int:
        self.pid_counter += 1
        return self.pid_counter

    def set_watcher_pid(self, collection_name: str, pid: int) -> None:
        watcher_path = self.app_dir / f"{collection_name}-watcher.json"
        self.running_watchers[str(watcher_path)] = pid

    def chroma_client(self) -> FakePersistentClient:
        return self.fake_client

    def _collection_doc_count(self, collection_name: str) -> int | None:
        try:
            return self.fake_client.get_collection(collection_name).count()
        except ValueError:
            return None


@pytest.fixture
def kb_env(tmp_path, monkeypatch):
    return KBTestEnv(tmp_path, monkeypatch)
