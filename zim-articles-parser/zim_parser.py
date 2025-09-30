# pip install libzim markdownify
from __future__ import annotations

import re
import json
from datetime import datetime, timezone
from pathlib import Path
from libzim.reader import Archive
from libzim.search import Searcher, Query
from markdownify import markdownify as html2md

ISO_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

def safe_slug(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)   # filesystem-safe
    return s.strip()[:180] or "untitled"

def extract_timestamps(html: str) -> tuple[str | None, str | None]:
    """Pull ISO-8601 timestamps out of the HTML, best-effort."""
    modification = creation = None
    iso_values: list[str] = []

    for match in ISO_PATTERN.finditer(html):
        iso = match.group(0)
        iso_values.append(iso)
        context = html[max(0, match.start() - 80):match.start()].lower()
        if not modification and any(key in context for key in ("modification", "modified", "updated", "lastedit", "last-edit")):
            modification = iso
            continue
        if not creation and any(key in context for key in ("creation", "created", "publish", "createdtime", "created-time")):
            creation = iso

    if not modification and iso_values:
        modification = iso_values[0]
    if not creation and iso_values:
        creation = iso_values[-1] if len(iso_values) > 1 else iso_values[0]

    return modification, creation


def extract_zim(zim_path: str, out_dir: str | None, limit: int | None = None, json_path: str | None = None):
    out = Path(out_dir) if out_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    run_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    zim = Archive(zim_path)
    try:
        print(f"Entries (user): {zim.entry_count}, articles: {zim.article_count}")
        print(f"Main entry path: {zim.main_entry.path if zim.has_main_entry else '—'}")

        # Strategy A: enumerate via title index if available (fast & ordered)
        titles = []
        if zim.has_title_index:
            print("Collecting titles via title index…")
            # Pull suggestions in batches by alphabet (cheap way to walk the title index)
            # You can also jump by prefixes 'a', 'b', ... 'z', '0-9' to cover the space.
            from libzim.suggestion import SuggestionSearcher
            sugg = SuggestionSearcher(zim)
            for prefix in list("0123456789abcdefghijklmnopqrstuvwxyz"):
                res = sugg.suggest(prefix)
                n = res.getEstimatedMatches()
                if n:
                    print(f"  prefix '{prefix}': +{n} matches")
                titles.extend(res.getResults(0, n))
            print(f"Title suggestions collected: {len(titles)} (pre-dedupe)")
        else:
            # Strategy B: fall back to full-text (broader, slower). Query everything with '*'
            if zim.has_fulltext_index:
                print("Collecting titles via full-text index…")
                q = Query().set_query("*")
                search = Searcher(zim).search(q)
                n = search.getEstimatedMatches()
                titles = [r.title for r in search.getResults(0, n)]
                print(f"Full-text search returned ~{n} matches")
            else:
                raise RuntimeError("No title index or full-text index found; enumeration not available.")

        # De-duplicate while keeping order
        seen = set(); titles = [t for t in titles if not (t in seen or seen.add(t))]
        print(f"Unique titles to process: {len(titles)}")

        count = 0
        processed = 0
        for title in titles:
            if limit and count >= limit: break
            processed += 1
            try:
                entry = zim.get_entry_by_title(title)
            except KeyError:
                continue

            # Follow redirects
            if entry.is_redirect:
                try:
                    entry = entry.get_redirect_entry()
                except KeyError:
                    continue

            item = entry.get_item()
            if not item or not item.mimetype.startswith("text/html"):
                continue

            html = bytes(item.content).decode("utf-8", errors="ignore")
            md = html2md(html)

            markdown_output = f"# {item.title}\n\n{md}"

            if out:
                # File path mirrors ZIM path; change to .md
                rel = Path(item.path).with_suffix(".md")
                safe = Path(*[safe_slug(p) for p in rel.parts])
                out_path = out / safe
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(markdown_output, encoding="utf-8")

            modification, creation = extract_timestamps(html)
            if not modification:
                modification = run_timestamp
            if not creation:
                creation = run_timestamp
            records.append({
                "title": item.title,
                "markdown": markdown_output,
                "size": len(markdown_output.encode("utf-8")),
                "modificationDate": modification,
                "creationDate": creation,
            })

            count += 1
            if out and count % 100 == 0:
                print(f"Wrote {count} markdown files…")
            elif processed % 200 == 0:
                print(f"Processed {processed} titles so far; wrote {count}")

        if json_path:
            json_file = Path(json_path)
            json_file.parent.mkdir(parents=True, exist_ok=True)
            json_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Wrote JSON catalog for {len(records)} entries to {json_file.resolve()}")

        if out:
            print(f"Done. Wrote {count} Markdown files to {out.resolve()}")
        else:
            print(f"Done. Processed {count} Markdown articles (catalog only)")
    finally:
        if hasattr(zim, "close"):
            zim.close()

