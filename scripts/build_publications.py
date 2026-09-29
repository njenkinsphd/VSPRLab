#!/usr/bin/env python3
"""
Build publications.html from publications.json.

Keeps the VSPR design tokens in sync with index.html. Run after fetch_pubmed.py.

    python3 scripts/build_publications.py
"""

import argparse
import html
import json
from pathlib import Path
from collections import defaultdict

PI_SURNAME = "Jenkins"
PI_INITIAL_VARIANTS = {"ND", "NDM", "N", "NDMoyer"}
PI_CANONICAL = "Jenkins NDM"

GROUPS = [
    ("article",    "Peer-reviewed articles", "Original research reports."),
    ("review",     "Reviews and guidelines", "Invited reviews, consensus statements, and methodological guidelines."),
    ("commentary", "Editorials and commentary", "Invited commentary and correspondence."),
    ("preprint",   "Preprints", "Posted but not yet peer reviewed."),
    ("abstract",   "Conference abstracts", "Presented at scientific meetings."),
]


LAB_FILE = "lab_members.txt"
MANUAL_FILE = "manual_entries.json"


def load_manual(path=MANUAL_FILE):
    """Records from My Bibliography that PubMed does not index."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("records", [])
    except (json.JSONDecodeError, OSError) as exc:
        print("warning: could not read %s: %s" % (path, exc))
        return []


def parse_name(raw):
    """
    Accept 'Rogers EM' (PubMed form) or 'Emily Rogers' (natural form).
    Returns (surname_lower, initials_upper) or None.
    """
    toks = raw.replace(",", " ").split()
    if len(toks) < 2:
        return None
    last = toks[-1]
    # PubMed form: trailing token is a short all-caps initials blob.
    if last.isupper() and len(last) <= 4 and last.isalpha():
        surname = " ".join(toks[:-1])
        initials = last
    else:
        surname = last
        initials = "".join(t[0] for t in toks[:-1] if t[:1].isalpha())
    if not surname or not initials:
        return None
    return surname.lower(), initials.upper()


def load_lab(path=LAB_FILE):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parsed = parse_name(line)
        if parsed:
            out.append(parsed)
    return out


def is_lab(author, roster):
    """Surname must match; either initials string may be a prefix of the other."""
    parsed = parse_name(author)
    if not parsed:
        return False
    surname, initials = parsed
    for r_sur, r_ini in roster:
        if surname == r_sur and (initials.startswith(r_ini) or r_ini.startswith(initials)):
            return True
    return False


def normalize_author(a):
    """Render the PI's byline consistently, whatever initials PubMed recorded."""
    parts = a.split()
    if len(parts) == 2 and parts[0] == PI_SURNAME and parts[1] in PI_INITIAL_VARIANTS:
        return PI_CANONICAL
    return a


def author_html(authors, roster=()):
    out = []
    for a in authors:
        a = normalize_author(a)
        esc = html.escape(a)
        if a == PI_CANONICAL:
            out.append(f'<span class="pi" title="Principal investigator">{esc}</span>')
        elif is_lab(a, roster):
            out.append(f'<span class="member" title="VSPR Lab trainee or staff">{esc}</span>')
        else:
            out.append(esc)
    return ", ".join(out)


def citation_html(r):
    bits = [f'<span class="jrnl">{html.escape(r["journal"])}</span>']
    if r.get("year"):
        bits.append(str(r["year"]))
    loc = ""
    if r.get("volume"):
        loc = html.escape(r["volume"])
        if r.get("issue"):
            loc += f'({html.escape(r["issue"])})'
    if r.get("pages"):
        loc = f'{loc}:{html.escape(r["pages"])}' if loc else html.escape(r["pages"])
    if loc:
        bits.append(loc)
    return " &middot; ".join(bits)


def entry_html(r, roster=()):
    links = []
    if r.get("doi"):
        d = html.escape(r["doi"])
        links.append(f'<a href="https://doi.org/{d}" rel="noopener">doi</a>')
    if r.get("pmid"):
        p = html.escape(r["pmid"])
        links.append(f'<a href="https://pubmed.ncbi.nlm.nih.gov/{p}/" rel="noopener">pubmed</a>')
    if r.get("pmc"):
        c = html.escape(r["pmc"])
        links.append(f'<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/{c}/" rel="noopener">full text</a>')
    linkbar = f'<p class="pub-links">{" ".join(links)}</p>' if links else ""
    return (
        '<li class="pub">\n'
        f'        <p class="pub-authors">{author_html(r["authors"], roster)}</p>\n'
        f'        <h3 class="pub-title">{html.escape(r["title"])}</h3>\n'
        f'        <p class="pub-cite">{citation_html(r)}</p>\n'
        f'        {linkbar}\n'
        '      </li>'
    )


def build(data, roster=()):
    by_group = defaultdict(list)
    for r in data["records"]:
        by_group[r.get("group", "article")].append(r)

    sections = []
    nav_items = []
    for key, heading, blurb in GROUPS:
        recs = by_group.get(key, [])
        if not recs:
            continue
        nav_items.append(f'<a href="#{key}">{html.escape(heading)} <span>{len(recs)}</span></a>')

        years = defaultdict(list)
        for r in recs:
            years[r.get("year") or 0].append(r)

        blocks = []
        for y in sorted(years, reverse=True):
            items = "\n      ".join(entry_html(r, roster) for r in years[y])
            blocks.append(
                '<div class="year">\n'
                f'      <p class="year-label">{y or "n.d."}</p>\n'
                f'      <ul class="pub-list">\n      {items}\n      </ul>\n'
                '    </div>'
            )

        sections.append(
            f'<section class="group" id="{key}">\n'
            f'    <div class="group-head">\n'
            f'      <h2 class="group-title">{html.escape(heading)}</h2>\n'
            f'      <p class="group-blurb">{html.escape(blurb)}</p>\n'
            f'      <p class="group-count">{len(recs)}</p>\n'
            f'    </div>\n'
            + "\n    ".join(blocks)
            + '\n  </section>'
        )

    return TEMPLATE.format(
        nav="\n      ".join(nav_items),
        sections="\n\n  ".join(sections),
        count=data["count"],
        generated=html.escape(data["generated"]),
        query=html.escape(data["query"]),
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Publications · VSPR Lab</title>
<meta name="description" content="Publications from the Vascular Stress Physiology and Resilience Laboratory at the University of Wisconsin-Madison.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{{
  --paper:#F8F8F8; --paper-deep:#EFEFF0; --ink:#1D1C1F; --slate:#6B6A70;
  --crimson:#B50811; --crimson-deep:#7A0309; --gold:#BF9B54;
  --blue:#2A5D8F;
  --display:"Archivo",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --body:"Source Serif 4",Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --gutter:clamp(20px,5vw,84px);
  --rule:1px solid rgba(29,28,31,.13);
}}
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);
  font-size:17px;line-height:1.62;-webkit-font-smoothing:antialiased}}
img{{max-width:100%;height:auto;display:block}}

.masthead{{border-bottom:var(--rule);padding:14px var(--gutter);display:flex;
  align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap}}
.masthead-inst{{font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.14em;
  text-transform:uppercase;color:var(--slate);margin:0}}
.masthead-inst strong{{color:var(--ink);font-weight:700}}
.sitenav{{display:flex;gap:18px;font-family:var(--mono);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase}}
.sitenav a{{color:var(--slate);text-decoration:none;padding-bottom:2px;border-bottom:1px solid transparent}}
.sitenav a:hover{{color:var(--ink);border-bottom-color:var(--gold)}}
.sitenav a[aria-current="page"]{{color:var(--crimson);border-bottom-color:var(--crimson)}}
.hairline{{height:2px;background:var(--gold);opacity:.85}}

.pubhead{{max-width:1440px;margin:0 auto;padding:clamp(40px,6vw,76px) var(--gutter) clamp(20px,3vw,32px)}}
.pubhead h1{{font-family:var(--display);font-weight:800;letter-spacing:-.035em;
  font-size:clamp(2.4rem,6.5vw,4.6rem);line-height:1;margin:0 0 1rem}}
.pubhead p{{color:var(--slate);max-width:60ch;margin:0}}
.meta{{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;color:var(--slate);
  margin-top:1.4rem;line-height:1.9}}
.key{{display:flex;gap:20px;flex-wrap:wrap;margin:1.5rem 0 0;padding:0;list-style:none;
  font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase}}
.key li{{display:flex;align-items:center;gap:7px;color:var(--slate)}}
.key i{{width:9px;height:9px;border-radius:50%;display:block;flex:0 0 auto}}
.key .k-pi{{background:var(--crimson)}}
.key .k-tr{{background:var(--blue)}}

.jump{{max-width:1440px;margin:0 auto;padding:0 var(--gutter) clamp(26px,4vw,44px);
  display:flex;flex-wrap:wrap;gap:10px}}
.jump a{{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink);text-decoration:none;border:1px solid rgba(29,28,31,.18);
  border-radius:2px;padding:7px 11px}}
.jump a:hover{{border-color:var(--crimson);color:var(--crimson)}}
.jump a span{{color:var(--gold);margin-left:.45em;font-weight:700}}

.group{{max-width:1440px;margin:0 auto;padding:0 var(--gutter) clamp(30px,5vw,58px)}}
.group-head{{border-top:2px solid var(--ink);padding-top:14px;margin-bottom:clamp(18px,3vw,30px);
  display:grid;grid-template-columns:1fr auto;gap:6px 20px;align-items:baseline}}
.group-title{{font-family:var(--display);font-weight:700;font-size:clamp(1.25rem,2.4vw,1.7rem);
  letter-spacing:-.02em;margin:0}}
.group-blurb{{grid-column:1;font-size:.94rem;color:var(--slate);margin:0;max-width:56ch}}
.group-count{{grid-row:1;grid-column:2;font-family:var(--mono);font-size:11px;font-weight:700;
  letter-spacing:.1em;color:var(--crimson);margin:0}}

.year{{display:grid;grid-template-columns:minmax(0,1fr);gap:4px 26px;
  border-top:var(--rule);padding:clamp(14px,2vw,20px) 0}}
.year-label{{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.14em;
  color:var(--slate);margin:0}}
.pub-list{{list-style:none;margin:0;padding:0}}
.pub{{padding:0 0 clamp(14px,2vw,20px);max-width:76ch}}
.pub:last-child{{padding-bottom:0}}
.pub-authors{{font-size:.9rem;color:var(--slate);margin:0 0 .18rem;line-height:1.5}}
.pub-authors .pi{{color:var(--crimson);font-weight:600}}
.pub-authors .member{{color:var(--blue);font-weight:600}}
.pub-title{{font-family:var(--body);font-weight:600;font-size:1.06rem;line-height:1.38;
  margin:0 0 .28rem}}
.pub-cite{{font-family:var(--mono);font-size:10.5px;letter-spacing:.04em;color:var(--slate);margin:0}}
.pub-cite .jrnl{{color:var(--ink)}}
.pub-links{{font-family:var(--mono);font-size:10px;letter-spacing:.11em;text-transform:uppercase;
  margin:.4rem 0 0;display:flex;gap:12px;flex-wrap:wrap}}
.pub-links a{{color:var(--crimson);text-decoration:none;border-bottom:1px solid var(--gold)}}
.pub-links a:hover{{border-bottom-color:var(--crimson)}}

@media (min-width:860px){{
  .year{{grid-template-columns:76px minmax(0,1fr)}}
  .year-label{{padding-top:.28rem}}
}}

.foot{{border-top:var(--rule);padding:clamp(30px,4vw,48px) var(--gutter);max-width:1440px;
  margin:0 auto;display:flex;justify-content:space-between;gap:22px;flex-wrap:wrap;align-items:flex-end}}
.foot-name{{font-family:var(--display);font-weight:700;font-size:1.02rem;letter-spacing:-.01em;margin:0 0 .3rem}}
.foot-meta{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--slate);margin:0;line-height:1.9}}
.foot-meta a{{color:var(--crimson);text-decoration:none;border-bottom:1px solid var(--gold)}}
.foot-mark{{width:118px;opacity:.5}}
:where(a,button):focus-visible{{outline:2px solid var(--crimson);outline-offset:3px;border-radius:2px}}
</style>
</head>
<body>

<header class="masthead">
  <p class="masthead-inst"><strong>University of Wisconsin&ndash;Madison</strong> &middot; Department of Kinesiology</p>
  <nav class="sitenav">
    <a href="index.html">Home</a>
    <a href="publications.html" aria-current="page">Publications</a>
  </nav>
</header>
<div class="hairline" role="presentation"></div>

<main>
  <div class="pubhead">
    <h1>Publications</h1>
    <p>{count} indexed records from the lab and from Nathaniel D. M. Jenkins, grouped by type and listed newest first.</p>
    <p class="meta">
      Source PubMed, query <code>{query}</code><br>
      Last updated {generated}
    </p>
    <ul class="key">
      <li><i class="k-pi"></i> Principal investigator</li>
      <li><i class="k-tr"></i> VSPR Lab trainee or staff</li>
    </ul>
  </div>

  <nav class="jump" aria-label="Jump to section">
      {nav}
  </nav>

  {sections}
</main>

<footer class="foot">
  <div>
    <p class="foot-name">Vascular Stress Physiology and Resilience Laboratory</p>
    <p class="foot-meta">
      Department of Kinesiology &middot; University of Wisconsin&ndash;Madison<br>
      Bardeen / SMI &middot; 1300 University Ave, Madison, WI 53706<br>
      <a href="mailto:VSPRLab@wisc.edu">VSPRLab@wisc.edu</a>
    </p>
  </div>
  <img class="foot-mark" src="Media/VSPR Monogram (transparent).png" alt="">
</footer>

</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="publications.json")
    ap.add_argument("--out", default="publications.html")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)

    # Merge anything PubMed cannot supply. De-dupe on DOI then on title, so a
    # record that later gains a PMID does not show up twice.
    manual = load_manual()
    if manual:
        seen_doi = {(r.get("doi") or "").lower() for r in data["records"] if r.get("doi")}
        seen_title = {(r.get("title") or "").lower().strip() for r in data["records"]}
        added = [m for m in manual
                 if (m.get("doi") or "").lower() not in seen_doi
                 and (m.get("title") or "").lower().strip() not in seen_title]
        data["records"].extend(added)
        data["count"] = len(data["records"])
        data["records"].sort(key=lambda r: (-(r.get("year") or 0),
                                            (r.get("title") or "").lower()))
        print("merged %d non-PubMed record(s); %d already present"
              % (len(added), len(manual) - len(added)))

    roster = load_lab()
    page = build(data, roster)
    print(f"lab roster: {len(roster)} name(s)")
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote {args.out} from {data['count']} records")


if __name__ == "__main__":
    main()
