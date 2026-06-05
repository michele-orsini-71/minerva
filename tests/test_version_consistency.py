"""Guard: every Minerva package must declare the same version (lockstep release).

Each package declares its version once, as ``__version__`` in its package
``__init__.py``; the package's ``setup.py`` / ``pyproject.toml`` reads that value
at build time. This test fails if those per-package declarations drift apart, so
a forgotten package or a partial bump is caught in CI rather than after release.

Use ``scripts/bump-version.sh <version>`` to move every package at once.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that hold copies or third-party code, never source of truth.
_EXCLUDED_PARTS = {
    ".venv", "venv", "build", "dist", ".eggs", ".git",
    ".shiv", "__pycache__", "node_modules",
}


def _collect_package_versions() -> dict[str, str]:
    """Map each source package __init__.py (relative path) to its __version__."""
    versions: dict[str, str] = {}
    for path in REPO_ROOT.rglob("__init__.py"):
        rel = path.relative_to(REPO_ROOT)
        if set(rel.parts) & _EXCLUDED_PARTS or any(
            part.endswith(".egg-info") for part in rel.parts
        ):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        versions[str(rel)] = ast.literal_eval(node.value)
    return versions


def test_all_packages_share_one_version():
    versions = _collect_package_versions()
    assert versions, "no package declared __version__ — discovery is broken"
    distinct = set(versions.values())
    assert len(distinct) == 1, "package versions have drifted:\n" + "\n".join(
        f"  {path} = {ver}" for path, ver in sorted(versions.items())
    )
