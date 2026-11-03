#!/usr/bin/env python3
"""Write sitemap.xml from the HTML pages in the repo root.

lastmod comes from each file's git commit date, not its mtime, so a fresh
clone or a rebuild that touches every file does not claim everything changed
today. Pages are listed in the order below, which is also the nav order.
"""
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE = "https://njenkinsphd.github.io/VSPRLab/"

# path, priority. index.html is published as the bare directory URL.
PAGES = [
    ("index.html", "1.0"),
    ("people.html", "0.8"),
    ("lab.html", "0.8"),
    ("publications.html", "0.8"),
    ("join.html", "0.8"),
]


def last_commit_date(path):
    """Commit date of the file, or today if it has changes not yet committed.

    The uncommitted check matters in CI, where the sitemap is written in the
    same run that regenerates a page but before that page is committed.
    """
    today = date.today().isoformat()
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", path],
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            return today
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", path],
            capture_output=True, text=True, check=True).stdout.strip()
        return out or today
    except Exception:
        return today


def main():
    root = Path(__file__).resolve().parent.parent
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    n = 0
    for name, priority in PAGES:
        if not (root / name).exists():
            print(f"  skipping {name}, not found", file=sys.stderr)
            continue
        loc = BASE if name == "index.html" else BASE + name
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{last_commit_date(name)}</lastmod>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
        n += 1
    lines.append("</urlset>")
    (root / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote sitemap.xml with {n} urls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
