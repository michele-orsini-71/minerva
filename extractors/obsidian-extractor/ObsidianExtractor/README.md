# Obsidian Extractor

A standalone .NET CLI that converts an Obsidian vault (a directory of markdown files) into the Minerva Note Schema so the notes can be indexed just like any other extractor output.

## Requirements
- .NET 10 SDK or newer (`dotnet --version` ≥ 10). If you only have newer runtimes installed, run commands with `DOTNET_ROLL_FORWARD=LatestMajor` to reuse them.
- Access to the Obsidian vault on disk (the extractor walks the directory tree, skipping `.obsidian`, `.git`, virtualenvs, etc.).

## Quick Start
```bash
cd extractors/obsidian-extractor
# Build once to produce the CLI binary
DOTNET_ROLL_FORWARD=LatestMajor dotnet build src/ObsidianExtractor/ObsidianExtractor.csproj

# Export markdown notes to JSON
DOTNET_ROLL_FORWARD=LatestMajor dotnet run \
  --project src/ObsidianExtractor/ObsidianExtractor.csproj -- \
  /path/to/vault -o notes.json -v

# Validate and index downstream
minerva validate notes.json --verbose
minerva index --config configs/obsidian.json --verbose
```

## CLI Options
```
obsidian-extractor <directory> [options]
  -o, --output <file>      Write JSON output to file (defaults to stdout)
  -v, --verbose           Print scan/extract progress to stderr
      --exclude <pattern>  Skip directories whose name matches (repeatable)
      --scan-only          List directories that contain markdown files
  -h, --help              Show usage help
```

`--scan-only` ignores `-o/--output` on purpose so you can explore the vault structure without overwriting files. Use `--exclude` multiple times to skip plugin folders or archives. Default excludes already cover `.git`, `node_modules`, `__pycache__`, `.venv`, `.obsidian`, etc.

## Output Schema
The extractor emits a JSON array of notes following the [Minerva Note Schema](../../docs/NOTE_SCHEMA.md). Each note captures:
- `title`: The first markdown H1 in the file or the filename.
- `markdown`: Raw markdown contents.
- `size`: UTF-8 byte length of the markdown.
- `modificationDate` / `creationDate`: UTC timestamps formatted as ISO 8601.
- `sourcePath`: Vault-relative path (POSIX separators) to help trace originals.

## Development
- The code lives in `src/ObsidianExtractor` and builds as a simple console app.
- `dotnet test` is not required yet (there are no unit tests), but please run `dotnet build` plus `DOTNET_ROLL_FORWARD=LatestMajor dotnet run -- --help` to ensure the CLI works.
- When contributing improvements, update this README and add fixture instructions under `test-data/` if you introduce new scenarios.
