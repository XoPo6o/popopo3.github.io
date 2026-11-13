#!/usr/bin/env python3
"""Dependency-free checks for the static salon website."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys

ROOT = Path(__file__).resolve().parents[2]
HTML_FILE = ROOT / "index.html"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.references = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)

        for attr in ("href", "src"):
            value = attrs.get(attr)
            if value:
                self.references.append((tag, attr, value))


def main():
    if not HTML_FILE.is_file():
        print("ERROR: index.html was not found")
        return 1

    parser = SiteParser()
    parser.feed(HTML_FILE.read_text(encoding="utf-8"))
    parser.close()

    errors = []
    id_set = set()
    for element_id in parser.ids:
        if element_id in id_set:
            errors.append(f"Duplicate id: #{element_id}")
        id_set.add(element_id)

    checked_assets = 0
    checked_anchors = 0

    for tag, attr, raw_value in parser.references:
        value = raw_value.strip()
        if not value:
            continue

        parsed = urlsplit(value)

        if attr == "href" and parsed.scheme == "" and parsed.netloc == "" and parsed.path == "":
            target = parsed.fragment
            if target:
                checked_anchors += 1
                if target not in id_set:
                    errors.append(f"Broken anchor: {value}")
            continue

        if parsed.scheme or parsed.netloc:
            continue

        if attr == "href" and parsed.path == "":
            continue

        local_path = unquote(parsed.path)
        if not local_path:
            continue

        resolved = (ROOT / local_path.lstrip("/")).resolve()
        if not resolved.is_relative_to(ROOT.resolve()):
            errors.append(f"Path escapes repository: {raw_value}")
            continue

        checked_assets += 1
        if not resolved.is_file():
            errors.append(f"Missing local file referenced by {tag}[{attr}]: {raw_value}")

    if errors:
        print("Static site validation FAILED:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Static site validation PASSED")
    print(f"Unique IDs: {len(id_set)}")
    print(f"Internal anchors checked: {checked_anchors}")
    print(f"Local files checked: {checked_assets}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
