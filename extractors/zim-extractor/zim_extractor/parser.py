"""Utilities for extracting structured notes from ZIM archives."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

from libzim.reader import Archive
from libzim.search import Searcher, Query
from markdownify import markdownify as html2md

ISO_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def safe_slug(value: str) -> str:
    value = re.sub(r'[\/:*?"<>|]+', '_', value)
    return value.strip()[:180] or "untitled"


def extract_timestamps(html: str) -> tuple[str | None, str | None]:
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


def extract_zim(
    zim_path: str,
    markdown_dir: str | None = None,
    limit: int | None = None,
    verbose: bool = False,
) -> List[Dict[str, object]]:
    out_dir = Path(markdown_dir) if markdown_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    run_timestamp = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    zim = Archive(zim_path)
    try:
        if verbose:
            print(
                f"Entries (user): {zim.entry_count}, articles: {zim.article_count}",
                file=sys.stderr,
            )
            main_entry = zim.main_entry.path if zim.has_main_entry else "—"
            print(f"Main entry path: {main_entry}", file=sys.stderr)

        titles: list[str] = []
        if zim.has_title_index:
            if verbose:
                print("Collecting titles via title index…", file=sys.stderr)
            from libzim.suggestion import SuggestionSearcher

            sugg = SuggestionSearcher(zim)
            for prefix in list("0123456789abcdefghijklmnopqrstuvwxyz"):
                res = sugg.suggest(prefix)
                count = res.getEstimatedMatches()
                if verbose and count:
                    print(f"  prefix '{prefix}': +{count} matches", file=sys.stderr)
                titles.extend(res.getResults(0, count))
        elif zim.has_fulltext_index:
            if verbose:
                print("Collecting titles via full-text index…", file=sys.stderr)
            query = Query().set_query("*")
            search = Searcher(zim).search(query)
            estimated = search.getEstimatedMatches()
            titles = [result.title for result in search.getResults(0, estimated)]
            if verbose:
                print(f"Full-text search returned ~{estimated} matches", file=sys.stderr)
        else:
            raise RuntimeError("No title index or full-text index found; enumeration not available.")

        seen: set[str] = set()
        deduped_titles = []
        for title in titles:
            if title not in seen:
                seen.add(title)
                deduped_titles.append(title)
        titles = deduped_titles

        if verbose:
            print(f"Unique titles to process: {len(titles)}", file=sys.stderr)

        count = 0
        processed = 0
        for title in titles:
            if limit is not None and count >= limit:
                break

            processed += 1
            try:
                entry = zim.get_entry_by_title(title)
            except KeyError:
                continue

            if entry.is_redirect:
                try:
                    entry = entry.get_redirect_entry()
                except KeyError:
                    continue

            item = entry.get_item()
            if not item or not item.mimetype.startswith("text/html"):
                continue

            html = bytes(item.content).decode("utf-8", errors="ignore")
            markdown = html2md(html)
            markdown_output = f"# {item.title}\n\n{markdown}"

            if out_dir:
                relative = Path(item.path).with_suffix(".md")
                safe_parts = [safe_slug(part) for part in relative.parts]
                output_path = out_dir.joinpath(*safe_parts)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(markdown_output, encoding="utf-8")

            modification, creation = extract_timestamps(html)
            if not modification:
                modification = run_timestamp
            if not creation:
                creation = run_timestamp

            records.append(
                {
                    "title": item.title,
                    "markdown": markdown_output,
                    "size": len(markdown_output.encode("utf-8")),
                    "modificationDate": modification,
                    "creationDate": creation,
                }
            )

            count += 1
            if verbose and processed % 200 == 0:
                print(
                    f"Processed {processed} titles so far; captured {count} markdown articles",
                    file=sys.stderr,
                )
            if verbose and out_dir and count % 100 == 0:
                print(f"Wrote {count} markdown files…", file=sys.stderr)

        if verbose:
            destination = out_dir.resolve() if out_dir else "stdout"
            print(f"Done. Generated {len(records)} records (markdown -> {destination})", file=sys.stderr)
    finally:
        if hasattr(zim, "close"):
            zim.close()

    return records
