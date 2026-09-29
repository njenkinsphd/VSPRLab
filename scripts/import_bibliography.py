#!/usr/bin/env python3
"""
Turn a My NCBI "My Bibliography" export into two files:

  pmids_include.txt    PMIDs the PubMed fetch must always include
  manual_entries.json  records with NO PMID, which PubMed cannot supply

My Bibliography is the curated, authoritative list, and it holds work PubMed
does not index: conference abstracts, and papers in journals outside MEDLINE.
Those records carry no PMID line, so a PMID-only importer drops them silently.
This one keeps them.

NCBI's robots.txt disallows automated crawling of /myncbi/, so this reads a
file you download rather than scraping the page.

How to get the file:
    1. Sign in to My NCBI, open My Bibliography
    2. Select all citations
    3. Download, choosing MEDLINE format. It carries the non-PubMed records
       too, which a plain PMID list does not.
    4. Run this script on it

Usage:
    python3 scripts/import_bibliography.py medline.txt
"""

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

PMID_URL = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{4,9})")
PMID_BARE = re.compile(r"^\s*(\d{4,9})\s*$", re.M)
SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}

ABSTRACT_TITLE_HINTS = ("abstract",)
# Conference proceedings ride in supplement issues: "Suppl_1", "S1", "SI".
SUPPL_ISSUE = re.compile(r"^\s*(s(uppl)?[\s_.-]*\d*|si)\s*$", re.I)


def split_records(text):
    return [r for r in re.split(r"\n\s*\n", text) if r.strip()]


def unfold(rec):
    """MEDLINE wraps long values onto indented continuation lines."""
    out, cur = [], None
    for line in rec.splitlines():
        if re.match(r"^[A-Z]{2,4}\s*-\s", line):
            if cur:
                out.append(cur)
            cur = line
        elif cur is not None and line.startswith(" "):
            cur += " " + line.strip()
    if cur:
        out.append(cur)
    return out


def tags(rec):
    d = {}
    for line in unfold(rec):
        m = re.match(r"^([A-Z]{2,4})\s*-\s*(.*)$", line)
        if m:
            d.setdefault(m.group(1), []).append(m.group(2).strip())
    return d


def author_from_au(raw):
    """
    Non-PubMed records write authors as 'Surname,Given Names,'.
    'Power,Gavin,'            -> 'Power G'
    'Lima Oliveira,Manoela,'  -> 'Lima Oliveira M'
    'Lewis,Jr.,Robert'        -> 'Lewis R'
    An already-normalized 'Jenkins NDM' passes through unchanged.
    """
    raw = raw.strip().rstrip(",")
    if "," not in raw:
        return raw
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    surname = parts[0]
    given = [p for p in parts[1:] if p.lower().rstrip(".") not in SUFFIXES]
    def letters(tok):
        # "DM" and "D.M." are already initials: keep every letter.
        # "Nathaniel" is a name: keep only the first.
        return tok if (tok.isupper() and len(tok) <= 4) else tok[0]

    initials = "".join(
        letters(tok) for chunk in given for tok in re.split(r"[\s.\-]+", chunk)
        if tok and tok[0].isalpha()
    ).upper()
    return (surname + " " + initials).strip()


def year_from_dp(dp):
    m = re.search(r"(19|20)\d{2}", dp or "")
    return int(m.group(0)) if m else None


def manual_record(t):
    title = (t.get("TI", [""])[0] or "").rstrip(".")
    issue = t.get("IP", [None])[0]
    is_abstract = (
        bool(issue and SUPPL_ISSUE.match(issue))
        or any(h in title.lower() for h in ABSTRACT_TITLE_HINTS)
        or bool(t.get("CT"))          # MEDLINE conference-title tag
    )
    return {
        "pmid": None,
        "doi": t.get("DO", [None])[0],
        "pmc": None,
        "title": title,
        "authors": [author_from_au(a) for a in t.get("AU", [])],
        "journal": t.get("TA", [None])[0] or t.get("PB", [""])[0],
        "year": year_from_dp(t.get("DP", [None])[0]),
        "volume": t.get("VI", [None])[0],
        "issue": issue,
        "pages": t.get("PG", [None])[0],
        "group": "abstract" if is_abstract else "article",
        "article_types": ["Not indexed in PubMed"],
        "source": "bibliography",
    }


def from_csv(text):
    found = []
    try:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return found
        key = next((f for f in reader.fieldnames
                    if f and f.strip().lower().replace(" ", "") in
                    {"pmid", "pubmedid", "pubmed_id", "accession"}), None)
        if not key:
            return found
        for row in reader:
            m = re.search(r"\d{4,9}", (row.get(key) or "").strip())
            if m:
                found.append(m.group(0))
    except csv.Error:
        pass
    return found


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export", help="file downloaded from My Bibliography")
    ap.add_argument("--out", default="pmids_include.txt")
    ap.add_argument("--manual-out", default="manual_entries.json")
    args = ap.parse_args()

    path = Path(args.export)
    if not path.exists():
        print("no such file: " + str(path), file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")

    pmids, manual, fmt = [], [], None
    records = split_records(text)

    # MEDLINE is the only export that carries the non-PubMed records.
    if any(re.search(r"^(PMID|TI|FAU|AU)\s*-\s", r, re.M) for r in records):
        fmt = "MEDLINE"
        for r in records:
            t = tags(r)
            if "PMID" in t:
                pmids.append(t["PMID"][0])
            elif "TI" in t:
                manual.append(manual_record(t))

    if not pmids:
        for label, hits in (("CSV", from_csv(text)),
                            ("URL", PMID_URL.findall(text)),
                            ("plain PMID list", PMID_BARE.findall(text))):
            if hits:
                fmt, pmids = label, hits
                break

    if not pmids and not manual:
        print("Found nothing usable in " + path.name, file=sys.stderr)
        print("Re-download from My Bibliography as MEDLINE.", file=sys.stderr)
        return 1

    pmids = dedupe(pmids)
    Path(args.out).write_text(
        "# PMIDs from Nathaniel D. M. Jenkins' My NCBI bibliography.\n"
        "# Regenerate with: python3 scripts/import_bibliography.py " + path.name + "\n"
        "# Always included, even if the PubMed author query misses them.\n"
        + "\n".join(pmids) + "\n", encoding="utf-8")

    if manual:
        Path(args.manual_out).write_text(
            json.dumps({"source": "My Bibliography (not indexed in PubMed)",
                        "count": len(manual), "records": manual},
                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("parsed " + path.name + " as " + str(fmt))
    print("  " + str(len(pmids)) + " PMIDs -> " + args.out)
    if manual:
        print("  " + str(len(manual)) + " records with NO PMID -> " + args.manual_out)
        by_j = {}
        for r in manual:
            key = r["journal"] or "(no journal)"
            by_j[key] = by_j.get(key, 0) + 1
        for j, n in sorted(by_j.items(), key=lambda x: -x[1]):
            print("      %3d  %s" % (n, j))
        print("  Check manual_entries.json: the group field is a guess, not a fact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
