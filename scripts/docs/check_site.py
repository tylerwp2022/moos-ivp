"""Validate the rendered handbook and retain website source identity.

2026-11-20: Added local link, anchor, asset, and search checks.
Human contributor: Timeo Williams; acting agent: Cline/ChatGPT.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.errors = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("id", "name" if tag == "a" else "id"):
            if attrs.get(key):
                self.ids.add(attrs[key])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == "img" and not attrs.get("alt"):
            self.errors.append("image has no alternative text")


def check_site(root):
    root = root.resolve()
    pages = {path.resolve(): Page(path.read_text(encoding="utf-8"))
             for path in root.rglob("*.html")}
    errors = []
    checked = 0
    if not (root / "index.html").is_file():
        errors.append("missing index.html")
    for source, page in pages.items():
        errors.extend(f"{source.relative_to(root)}: {error}" for error in page.errors)
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                continue
            # Project Pages lives below /moos-ivp/, not at the domain root.
            path = unquote(parts.path)
            if path.startswith("/moos-ivp/"):
                target = root / path[len("/moos-ivp/"):]
            elif path.startswith("/"):
                errors.append(f"{source.relative_to(root)}: root-relative URL {link}")
                continue
            else:
                target = source.parent / path if path else source
            target = target.resolve()
            if not target.is_relative_to(root):
                errors.append(f"{source.relative_to(root)}: URL leaves site: {link}")
                continue
            if target.is_dir():
                target /= "index.html"
            checked += 1
            if not target.is_file():
                errors.append(f"{source.relative_to(root)}: missing target {link}")
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                errors.append(f"{source.relative_to(root)}: missing anchor {link}")
    search = root / "search/search_index.json"
    if not search.is_file() or not json.loads(search.read_text(encoding="utf-8")).get("docs"):
        errors.append("missing or empty search index")
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlink is not allowed in Pages artifact: {path.relative_to(root)}")
    return {"html_pages": len(pages), "local_links_checked": checked, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path, nargs="?", default=Path("site"))
    args = parser.parse_args()
    result = check_site(args.site)
    print(json.dumps(result, indent=2))
    if result["errors"]:
        return 1
    repository = Path(__file__).resolve().parents[2]
    def git(*command):
        return subprocess.check_output(
            ["git", "-c", f"safe.directory={repository.as_posix()}", "-C", str(repository), *command],
            text=True).strip()
    status = git("status", "--porcelain")
    metadata = {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "source_modified": bool(status),
        "source_status": status.splitlines(),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation": result,
        "note": "Website build identity; not a runtime verification date.",
    }
    (args.site / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
