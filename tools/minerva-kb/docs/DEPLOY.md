# minerva-kb Deployment and Distribution Guide

This document captures the architecture decisions, trade-offs, and approaches for deploying and distributing minerva-kb.

---

## Table of Contents

1. [Current Approach (Recommended)](#current-approach-recommended)
2. [Architecture Constraints](#architecture-constraints)
3. [Distribution Approaches Explored](#distribution-approaches-explored)
4. [Development Workflow](#development-workflow)
5. [Why Single-File Distribution is Difficult](#why-single-file-distribution-is-difficult)
6. [Future Considerations](#future-considerations)

---

## Current Approach (Recommended)

### Installation Script

**Recommended for users:** `./tools/minerva-kb/install.sh`

**What it does:**
1. Validates Python 3.10+ and pipx are installed
2. Installs minerva (core CLI) via pipx
3. Installs repository-doc-extractor via pipx
4. Installs local-repo-watcher via pipx
5. Installs minerva-kb via pipx
6. **Injects minerva-common** into minerva-kb's isolated venv

**Why this works:**
- ✅ All tools available in PATH
- ✅ Clean isolated environments (pipx)
- ✅ minerva-common bundled into minerva-kb (no separate installation)
- ✅ Simple one-command installation
- ✅ Easy to uninstall: `./tools/minerva-kb/uninstall.sh`

**Time to install:** ~2-3 minutes (including dependency downloads)

### User Experience

```bash
# Install everything
./tools/minerva-kb/install.sh

# Use it
minerva-kb add /path/to/repo
minerva-kb list
minerva-kb watch my-repo

# Uninstall everything
./tools/minerva-kb/uninstall.sh
```

---

## Architecture Constraints

### The Shared Library Problem

**Challenge:** minerva-kb depends on minerva-common (shared utilities), but minerva-common is **not published to PyPI**.

**Why minerva-common exists:**
- Shared code between minerva-kb and minerva-doc
- Avoids code duplication
- Provides common infrastructure (paths, registry, config builder, etc.)

**Why it's not on PyPI:**
- It's internal infrastructure, not a standalone library
- Would require separate versioning and release process
- Users shouldn't install it directly

**Solution:** Use `pipx inject` to bundle minerva-common into each tool's venv (like static linking in C or bundling in JavaScript).

### The Multi-Process Architecture

minerva-kb is actually a **orchestrator** that coordinates multiple independent tools:

```
┌─────────────┐
│ minerva-kb  │  ← Main CLI (user-facing)
└──────┬──────┘
       │
       ├─→ minerva (validate, index, remove, keychain)
       ├─→ repository-doc-extractor (extract docs from repos)
       └─→ local-repo-watcher (foreground file watcher)
```

**Key insight:** These are **separate processes**, not just function calls:

1. **minerva**: Synchronous operations (could be function calls)
2. **repository-doc-extractor**: Synchronous extraction (could be function call)
3. **local-repo-watcher**: **Long-running foreground process** (MUST be separate process!)

### Why the Watcher Must Be Separate

The file watcher:
- Runs as a **foreground process** (not a background daemon)
- Blocks the terminal while running (user sees file change events)
- Exits when `minerva-kb watch` exits (stopped with `Ctrl+C`)
- Is a separate executable (`local-repo-watcher`) launched via subprocess

**Cannot be a function call or thread** because:
- Long-running monitoring loop (watches for file changes continuously)
- Needs independent signal handling (clean shutdown on `Ctrl+C`)
- Requires its own process for resource isolation
- Must be interruptible without affecting minerva-kb

---

## Distribution Approaches Explored

### Approach 1: pipx install (Simple but Flawed)

```bash
pipx install /path/to/minerva-kb
```

**Problem:** Fails because minerva-common is not on PyPI.

```
ERROR: No matching distribution found for minerva-common
```

**Why this happens:**
- pipx creates an isolated virtual environment
- pip tries to install dependencies from PyPI
- minerva-common is a local package, not on PyPI

**Lesson:** pipx is for installing **applications**, not libraries. minerva-common has no CLI entry point, so pipx refuses to install it directly.

---

### Approach 2: pipx install + pipx inject (Current Solution ✅)

```bash
# Install the app
pipx install /path/to/minerva-kb

# Inject the library dependency
pipx inject minerva-kb /path/to/minerva-common
```

**How it works:**
- First command installs minerva-kb (fails without minerva-common dependency declared)
- Second command adds minerva-common to the same venv
- Result: minerva-kb can import from minerva-common

**Trade-offs:**
- ✅ Clean isolation
- ✅ No global pip pollution
- ✅ Uninstall removes everything
- ❌ Requires removing minerva-common from dependencies (not discoverable)
- ❌ Two-step process (hidden behind install.sh)

**Current implementation:**
- `tools/minerva-kb/pyproject.toml`: minerva-common removed from dependencies
- `tools/minerva-kb/install.sh`: Handles the inject step
- Comment in pyproject.toml explains the approach

---

### Approach 3: Shiv (.pyz Single Executable)

**Build command:**
```bash
./tools/minerva-kb/build-pyz.sh
```

**Result:** Single executable file `minerva-kb.pyz` (~302MB)

**What it contains:**
- ✅ minerva-kb Python code
- ✅ minerva-common Python code
- ✅ All Python dependencies (chromadb, openai, etc.)
- ✅ Even includes minerva, repository-doc-extractor, local-repo-watcher **as Python packages**

**What it DOESN'T provide:**
- ❌ CLI commands in PATH (minerva, repository-doc-extractor, local-repo-watcher)

**The critical limitation:**

When minerva-kb calls:
```python
subprocess.run(['minerva', 'index', '--config', config_path])
```

It looks for `minerva` in the **system PATH**, not inside the .pyz bundle!

**Why this happens:**
- Shiv bundles Python packages but only exposes **one entry point** (specified with `-c`)
- The .pyz runs in an isolated Python environment
- subprocess.run() searches the OS PATH, not the Python environment

**What would need to be installed separately:**
```bash
pipx install minerva
pipx install repository-doc-extractor
pipx install local-repo-watcher
./minerva-kb.pyz add /repo  # Now works!
```

**Verdict:** Defeats the "single file" purpose. Not truly standalone.

---

### Approach 4: PyPI (Public Distribution)

**Ideal for open source:**
```bash
pipx install minerva-kb
```

**Requirements:**
1. Publish minerva-common to PyPI (as a library)
2. Publish minerva-kb to PyPI (depends on minerva-common)
3. User also needs: minerva, repository-doc-extractor, local-repo-watcher

**Pros:**
- ✅ Standard Python distribution
- ✅ One command install
- ✅ Automatic updates
- ✅ Version management

**Cons:**
- ❌ Requires public release
- ❌ Need to version and publish minerva-common separately
- ❌ Still need to install 4 separate packages
- ❌ Or create a meta-package that depends on all of them

**Future option** if minerva becomes open source.

---

### Approach 5: Wheel Files (.whl)

**Build wheels:**
```bash
cd tools/minerva-common && python -m build --wheel
cd tools/minerva-kb && python -m build --wheel
```

**Distribution:**
```bash
# Share two files:
# - minerva_common-1.0.0-py3-none-any.whl (~10KB)
# - minerva_kb-1.0.0-py3-none-any.whl (~32KB)

# User installs:
pipx install minerva_kb-1.0.0-py3-none-any.whl
pipx inject minerva-kb minerva_common-1.0.0-py3-none-any.whl
```

**Trade-offs:**
- ✅ Small files
- ✅ Private distribution
- ✅ Standard format
- ❌ Still two commands
- ❌ Still need minerva, extractor, watcher installed

**Use case:** Alternative to install.sh for manual installation.

---

### Approach 6: PyInstaller (True Standalone Binary)

**Not explored in detail, but theoretically:**

```bash
pyinstaller --onefile minerva-kb
# Creates: dist/minerva-kb (~200MB+ with Python interpreter)
```

**Pros:**
- ✅ Truly standalone (includes Python)
- ✅ No Python required on user system
- ✅ Single binary

**Cons:**
- ❌ **Platform-specific** (must build on macOS for macOS, Linux for Linux, etc.)
- ❌ Very large file size (~200-500MB)
- ❌ **Still has subprocess problem** - would need to bundle minerva/extractor/watcher binaries
- ❌ Complex build process
- ❌ Slower startup

**Verdict:** Not worth the complexity for this use case.

---

## Development Workflow

### Active Development (Fast Iteration)

**DO NOT use .pyz for development** - rebuilding takes ~2 minutes!

**Option A: pipx with reinstall (Recommended)**
```bash
# Initial install
./tools/minerva-kb/install.sh

# After making changes:
pipx install --force tools/minerva-kb
pipx inject minerva-kb tools/minerva-common --force

# Test immediately
minerva-kb add /test/repo
```

**Option B: pip editable install (Fastest)**
```bash
# One-time setup
pip install -e tools/minerva-common
pip install -e tools/minerva-kb
pip install -e .  # minerva core
pipx install extractors/repository-doc-extractor
pipx install tools/local-repo-watcher

# Make changes, test immediately (no reinstall needed!)
minerva-kb add /test/repo
```

**Pros/cons:**
- ✅ Instant feedback (no reinstall)
- ✅ Changes reflected immediately
- ❌ Pollutes global Python environment
- ❌ Not isolated like pipx

### Integration Testing

**Before releasing, test with install.sh:**
```bash
./tools/minerva-kb/uninstall.sh
./tools/minerva-kb/install.sh
minerva-kb add /test/repo
```

**Or test with .pyz:**
```bash
./tools/minerva-kb/build-pyz.sh
./minerva-kb.pyz --version
./minerva-kb.pyz list
```

### Release Workflow

1. Update version in `pyproject.toml`
2. Test with install.sh (clean install)
3. Build .pyz (optional, for distribution)
4. Tag release in git
5. Share install.sh or .pyz with users

---

## Why Single-File Distribution is Difficult

### The Fundamental Problem

minerva-kb is not a monolithic application - it's an **orchestrator** of independent tools.

**What we'd need for true single-file distribution:**

1. Bundle all Python code ✅ (Shiv does this)
2. Expose all CLI commands ❌ (Shiv only exposes one entry point)
3. Handle subprocess calls ❌ (subprocess.run looks in OS PATH)

### Solutions Considered

#### Solution 1: Subprocess → Function Calls

**Replace this:**
```python
subprocess.run(['minerva', 'validate', 'file.json'])
```

**With this:**
```python
from minerva.commands.validate import run_validate
run_validate('file.json')
```

**What this solves:**
- ✅ minerva commands use bundled code (no separate install)
- ✅ repository-doc-extractor commands use bundled code

**What this DOESN'T solve:**
- ❌ local-repo-watcher **still needs to be a subprocess**
  - Long-running foreground process (blocks while monitoring)
  - Requires independent signal handling (Ctrl+C)
  - Cannot be a simple function call

**Verdict:** Solves 2 out of 3 dependencies, but still not fully standalone.

#### Solution 2: Bundle Watcher into minerva-kb

**Merge local-repo-watcher into minerva-kb:**
```
tools/minerva-kb/src/minerva_kb/watcher/
  ├── __init__.py
  ├── __main__.py  # Entry point for subprocess
  └── watcher.py
```

**Launch it:**
```python
subprocess.Popen([sys.executable, '-m', 'minerva_kb.watcher', ...])
```

**Pros:**
- ✅ Single .pyz file works standalone
- ✅ No separate watcher installation

**Cons:**
- ❌ Tight coupling (watcher can't be used independently)
- ❌ "Monster" minerva-kb package
- ❌ Watcher changes require minerva-kb rebuild
- ❌ **Same problem for minerva-doc later** (would need to duplicate watcher code)

**Verdict:** Violates separation of concerns. Not recommended.

#### Solution 3: Accept the Limitation

**Current approach:**
- Provide install.sh for best UX (handles everything)
- Provide .pyz for quick sharing (with documented dependencies)
- Accept that minerva-kb requires supporting tools

**Precedent:** Many CLI tools have dependencies:
- `git` has `git-lfs`, `git-flow`, etc.
- `docker` has `docker-compose`
- `npm` has `yarn`, `pnpm`

**Verdict:** Pragmatic and realistic. ✅

---

## Future Considerations

### If We Want Truly Standalone Distribution

**Option A: Refactor to direct imports + bundled watcher**
- Replace subprocess calls for minerva/extractor with direct imports
- Bundle watcher code into minerva-kb
- .pyz becomes standalone (except Python requirement)
- **Trade-off:** Increased coupling, larger codebase

**Option B: Create a "minerva-toolkit" meta-package**
- Publish to PyPI
- Depends on: minerva, minerva-kb, repository-doc-extractor, local-repo-watcher
- User installs once: `pipx install minerva-toolkit`
- **Trade-off:** Requires public release

**Option C: Keep current approach**
- install.sh is simple and works
- .pyz is a bonus for quick testing
- Don't over-engineer
- **Trade-off:** None (this is fine!)

### When to Revisit Subprocess Calls

**Consider refactoring if:**
1. Subprocess overhead becomes a performance bottleneck (unlikely)
2. We want true standalone .pyz distribution (maybe)
3. We're refactoring the architecture anyway (opportunistic)

**Don't refactor if:**
1. Current approach works fine ✅
2. Other priorities are more important ✅ (like minerva-doc)
3. The watcher still needs to be separate ✅

### minerva-doc Will Have the Same Challenges

When implementing minerva-doc:
- Same dependency on minerva-common
- Same subprocess calls to minerva
- Same need for install script
- **Don't reinvent the wheel** - use the same patterns!

---

## Summary: What Works and Why

### For Users (Distribution)

**Recommended:** Install script
```bash
./tools/minerva-kb/install.sh
```

**Why:** Handles all dependencies, clean installation, easy to uninstall.

**Alternative:** .pyz file (requires separate installation of dependencies)
```bash
# Install dependencies first
./tools/minerva-kb/install.sh  # Or manual pipx installs

# Then use .pyz
./minerva-kb.pyz add /repo
```

### For Developers (Development)

**Fast iteration:**
```bash
pip install -e tools/minerva-common
pip install -e tools/minerva-kb
# Edit code, test immediately
```

**Integration testing:**
```bash
./tools/minerva-kb/install.sh
# Test in isolated environment
```

### Architecture Decision

**Accept the multi-process architecture:**
- minerva-kb orchestrates multiple tools
- Each tool is independent and reusable
- Install script provides good UX
- Don't force everything into a single file

**Document the limitations:**
- .pyz is not truly standalone (requires dependencies)
- This is a known trade-off
- Users should use install.sh for best experience

---

## References

- **pipx documentation**: https://pipx.pypa.io/
- **Shiv documentation**: https://shiv.readthedocs.io/
- **Python packaging guide**: https://packaging.python.org/
- **Related files**:
  - `tools/minerva-kb/install.sh` - Installation script
  - `tools/minerva-kb/uninstall.sh` - Uninstallation script
  - `tools/minerva-kb/build-pyz.sh` - .pyz build script
  - `tools/minerva-kb/pyproject.toml` - Package configuration
  - `tools/minerva-common/` - Shared library
