#!/usr/bin/env bash
# Show which Minerva tools from THIS repo are installed via pipx, with their
# version and whether the install is editable (live from source) or a copy.
#
# The previous version ran `pip list --editable`, which inspected whatever
# virtualenv happened to be active — not the pipx-managed tools. This reads
# pipx directly and filters to packages whose source path is inside this repo.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export REPO_ROOT

pipx list --json | python3 -c '
import json, os, sys

repo = os.environ["REPO_ROOT"]
data = json.load(sys.stdin)
rows = []

def add(name, info, parent=None):
    url = info.get("package_or_url") or ""
    if not url.startswith(repo):
        return
    args = info.get("pip_args") or []
    mode = "editable" if ("--editable" in args or "-e" in args) else "copy"
    rel = os.path.relpath(url, repo)
    label = name if parent is None else name + " (-> " + parent + ")"
    rows.append((label, str(info.get("package_version", "?")), mode, rel))

for venv, vinfo in sorted(data.get("venvs", {}).items()):
    meta = vinfo.get("metadata", {})
    main = meta.get("main_package", {})
    add(main.get("package", venv), main)
    for iname, ip in (meta.get("injected_packages") or {}).items():
        add(iname, ip, parent=main.get("package", venv))

if not rows:
    print("No Minerva tools from this repo are installed via pipx.")
    sys.exit(0)

w = max(len(r[0]) for r in rows)
print("Package".ljust(w) + "  Version  Mode      Source (rel. to repo)")
print("-" * (w + 45))
for name, ver, mode, rel in rows:
    print(name.ljust(w) + "  " + ver.ljust(7) + "  " + mode.ljust(8) + "  " + rel)
'
