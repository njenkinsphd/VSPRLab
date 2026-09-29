#!/usr/bin/env python3
"""
Fetch the VSPR Lab's PubMed record and write publications.json.

Queries NCBI E-utilities for Nathaniel D. M. Jenkins, normalizes each record to
the small schema the site needs, and applies a manual exclude list.

Usage:
    python3 scripts/fetch_pubmed.py [--out publications.json]

Note: NCBI asks that automated clients identify themselves and stay under
3 requests/second without an API key (10/second with one). Set NCBI_API_KEY in
the environment to use a key. Requests are batched and paced accordingly.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import date

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
QUERY = "Jenkins NDM[Author]"

INCLUDE_FILE = "pmids_include.txt"   # from My Bibliography, always included
EXCLUDE_FILE = "pmids_exclude.txt"   # never included, whatever the query says

TOOL = "vspr-lab-site"
EMAIL = "VSPRLab@wisc.edu"

# article_types -> display group, first match wins
GROUP_RULES = [
    ("preprint",   {"Preprint"}),
    ("commentary", {"Comment", "Editorial", "Letter"}),
    ("review",     {"Review", "Systematic Review", "Meta-Analysis", "Practice Guideline"}),
]


def read_pmid_file(path):
    """One PMID per line; blank lines and # comments ignored. Missing file is fine."""
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.isdigit():
            out.append(line)
    return out


def _params(extra):
    p = {"tool": TOOL, "email": EMAIL}
    key = os.environ.get("NCBI_API_KEY")
    if key:
        p["api_key"] = key
    p.update(extra)
    return urllib.parse.urlencode(p)


def _get(endpoint, extra, retries=3):
    url = f"{EUTILS}/{endpoint}?{_params(extra)}"
    delay = 1.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"{TOOL} ({EMAIL})"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} after {exc}", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def search():
    raw = _get("esearch.fcgi", {"db": "pubmed", "term": QUERY, "retmode": "json", "retmax": 1000})
    data = json.loads(raw)
    return data["esearchresult"]["idlist"]


def _text(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else None


def _initials(author):
    ini = _text(author, "Initials")
    if ini:
        return ini
    fore = _text(author, "ForeName") or ""
    return "".join(part[0] for part in fore.replace("-", " ").split() if part[:1].isalpha())


def parse_article(art):
    medline = art.find("MedlineCitation")
    if medline is None:
        return None
    pmid = _text(medline, "PMID")
    article = medline.find("Article")
    if article is None:
        return None

    title = (_text(article, "ArticleTitle") or "").rstrip(".")

    authors = []
    for a in article.findall("./AuthorList/Author"):
        last = _text(a, "LastName")
        if not last:
            coll = _text(a, "CollectiveName")
            if coll:
                authors.append(coll)
            continue
        ini = _initials(a)
        authors.append(f"{last} {ini}".strip())

    journal = _text(article, "./Journal/ISOAbbreviation") or _text(article, "./Journal/Title") or ""

    year = None
    for path in ("./Journal/JournalIssue/PubDate/Year", "./Journal/JournalIssue/PubDate/MedlineDate"):
        v = _text(article, path)
        if v:
            for tok in v.replace("-", " ").split():
                if tok.isdigit() and len(tok) == 4:
                    year = int(tok)
                    break
        if year:
            break

    types = [t.text for t in article.findall("./PublicationTypeList/PublicationType") if t.text]
    types = [t for t in types if not t.startswith("Research Support")]

    group = "article"
    for name, trigger in GROUP_RULES:
        if trigger & set(types):
            group = name
            break

    doi = pmc = None
    for aid in art.findall("./PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi":
            doi = (aid.text or "").strip() or None
        elif aid.get("IdType") == "pmc":
            pmc = (aid.text or "").strip() or None

    return {
        "pmid": pmid,
        "doi": doi,
        "pmc": pmc,
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "volume": _text(article, "./Journal/JournalIssue/Volume"),
        "issue": _text(article, "./Journal/JournalIssue/Issue"),
        "pages": _text(article, "./Pagination/MedlinePgn"),
        "group": group,
        "article_types": types,
    }


def fetch(pmids, batch=100):
    out = []
    for i in range(0, len(pmids), batch):
        chunk = pmids[i:i + batch]
        print(f"  fetching {i + 1}-{i + len(chunk)} of {len(pmids)}", file=sys.stderr)
        raw = _get("efetch.fcgi", {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"})
        root = ET.fromstring(raw)
        for art in root.findall("./PubmedArticle"):
            rec = parse_article(art)
            if rec:
                out.append(rec)
        time.sleep(0.4 if os.environ.get("NCBI_API_KEY") else 1.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="publications.json")
    args = ap.parse_args()

    print(f"searching PubMed for {QUERY!r}", file=sys.stderr)
    found = search()
    print(f"  query returned {len(found)}", file=sys.stderr)

    include = read_pmid_file(INCLUDE_FILE)
    exclude = set(read_pmid_file(EXCLUDE_FILE))

    # The curated bibliography wins. Anything it lists is included even if the
    # author query missed it; anything in the exclude list is dropped regardless.
    pmids = [p for p in dict.fromkeys(list(found) + include) if p not in exclude]

    if include:
        missed = [p for p in include if p not in set(found)]
        extra = [p for p in found if p not in set(include) and p not in exclude]
        print(f"  bibliography lists {len(include)}", file=sys.stderr)
        if missed:
            print(f"  + {len(missed)} in bibliography but NOT found by the query: "
                  f"{', '.join(missed)}", file=sys.stderr)
        if extra:
            print(f"  ! {len(extra)} found by the query but NOT in the bibliography "
                  f"(check these are yours): {', '.join(extra)}", file=sys.stderr)
    else:
        print(f"  no {INCLUDE_FILE}; relying on the author query alone. "
              f"Run import_bibliography.py to add your curated list.", file=sys.stderr)

    if exclude:
        print(f"  {len(exclude)} excluded by {EXCLUDE_FILE}", file=sys.stderr)
    print(f"  fetching {len(pmids)}", file=sys.stderr)

    records = fetch(pmids)
    records.sort(key=lambda r: (-(r["year"] or 0), r["title"].lower()))

    if not records:
        print("ERROR: no records parsed, refusing to overwrite", file=sys.stderr)
        return 1

    payload = {
        "source": "PubMed",
        "query": QUERY,
        "generated": date.today().isoformat(),
        "count": len(records),
        "records": records,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {args.out} with {len(records)} records", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
