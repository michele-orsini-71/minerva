# Local Repo Watcher Manager

Utility CLI that helps you start `local-repo-watcher` for any Minerva collection without
remembering full config paths.

## Features

- Lists all watcher configs under `~/.minerva/apps/local-repo-kb/`
- Lets you select a collection interactively
- Optionally specify `--collection` or `--config` directly
- Forwards additional args to `local-repo-watcher`

## Usage

```bash
# list collections and start one
minerva-local-watcher

# launch a specific collection by name
minerva-local-watcher --collection my-project

# pass extra args to local-repo-watcher
minerva-local-watcher --collection my-project -- --debounce 5
```

The watcher runs in the foreground; press `Ctrl+C` to stop it.
