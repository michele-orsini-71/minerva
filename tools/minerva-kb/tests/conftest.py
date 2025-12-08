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

from minerva_kb import constants as constants_mod
from minerva_kb.commands import add as add_cmd
from minerva_kb.commands import list as list_cmd
from minerva_kb.commands import remove as remove_cmd
from minerva_kb.commands import status as status_cmd
from minerva_kb.commands import sync as sync_cmd
from minerva_kb.commands import watch as watch_cmd
from minerva_kb.utils import config_helpers, config_loader, description_generator


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
        self.app_dir = tmp_path / "app"
        self.chroma_dir = tmp_path / "chromadb"
        self.repos_dir = tmp_path / "repositories"
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
        }

    def queue_provider(self, provider: dict[str, str] | None = None) -> None:
        self.provider_queue.append(provider or self.default_provider())

    def create_repo(self, name: str, *, with_readme: bool = True) -> Path:
        repo = self.repos_dir / name
        repo.mkdir()
        if with_readme:
            (repo / "README.md").write_text(f"# {name}\n")
        return repo

    def next_pid(self) -> int:
        self.pid_counter += 1
        return self.pid_counter

    def set_watcher_pid(self, collection_name: str, pid: int) -> None:
        watcher_path = self.app_dir / f"{collection_name}-watcher.json"
        self.running_watchers[str(watcher_path)] = pid

    def chroma_client(self) -> FakePersistentClient:
        return self.fake_client


@pytest.fixture
def kb_env(tmp_path, monkeypatch):
    return KBTestEnv(tmp_path, monkeypatch)
