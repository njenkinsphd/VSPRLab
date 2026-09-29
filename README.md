# VSPR Lab website

Static site for the Vascular Stress Physiology and Resilience Laboratory,
Department of Kinesiology, University of Wisconsin–Madison.

No build step and no framework. `index.html` and `publications.html` open
directly in a browser.

```
index.html                 Home. Hand-edited.
publications.html          GENERATED. Do not edit by hand.
publications.json          GENERATED. The PubMed record set.
Media/                     Monogram and images.
lab_members.txt            Trainees and staff, highlighted blue. Hand-maintained.
manual_entries.json        GENERATED. Work PubMed does not index.
pmids_include.txt          From your My Bibliography export. Always included.
pmids_exclude.txt          Never included. Wrong-author papers go here.
scripts/import_bibliography.py  My Bibliography export -> pmids_include.txt
scripts/fetch_pubmed.py    Queries PubMed, writes publications.json
scripts/build_publications.py  Reads publications.json, writes publications.html
.github/workflows/         Monthly job that runs both and commits the result
```

## Publications

The list is generated, not maintained by hand. Editing `publications.html`
directly will lose your changes the next time the job runs.

To refresh locally:

```
python3 scripts/fetch_pubmed.py
python3 scripts/build_publications.py
```

Both use only the Python standard library.

### Where the list comes from

Two sources, combined:

1. **Your My NCBI bibliography** — the authoritative, curated list.
2. **A PubMed author query** — `Jenkins NDM[Author]`, so new papers appear on
   their own without you doing anything.

The final set is (query results + `pmids_include.txt`) - `pmids_exclude.txt`.
Your bibliography always wins. Anything it lists is included even if the query
misses it, and anything in the exclude list is dropped no matter what.

NCBI's `robots.txt` disallows automated crawling of `/myncbi/`, so nothing here
scrapes your bibliography page. You export it and the script reads the file:

```
# My NCBI > My Bibliography > select all > Download
# (PMID list, MEDLINE/.nbib, RIS, or CSV all work)
python3 scripts/import_bibliography.py ~/Downloads/bibliography.nbib
```

That writes two files, and you commit both:

- `pmids_include.txt` - PMIDs the fetch always includes
- `manual_entries.json` - records with **no PMID**

The second file matters. My Bibliography holds work PubMed does not index:
conference abstracts in Physiology and Circulation, and papers in journals
outside MEDLINE such as Isokinetics and Exercise Science, Journal of Exercise
Physiology Online, and Strength and Conditioning Journal. A PMID-only importer
drops every one of them without saying so. These records are merged into the
page at build time, de-duped on DOI and then on title, so one that later gains
a PMID will not appear twice.

Download as **MEDLINE**, not as a PMID list. A PMID list cannot carry the
records that have no PMID.

Re-run whenever you add citations to My Bibliography.

Every run prints a reconciliation: PMIDs in your bibliography the query missed,
and PMIDs the query found that your bibliography does not list. The second list
is worth a glance — that is where a wrong Jenkins would show up.

### Why the query is narrow

`Jenkins NDM[Author]` returns 108. The looser `Jenkins ND[Author]` returns 121
and pulls in a different N.D. Jenkins, including a 1994 paper on melanin in
*Cryptococcus neoformans* (PMID 8063430, already in `pmids_exclude.txt`).
Do not loosen it.

### Grouping

Records are sorted into five sections. PubMed records use PubMed's own
publication types, first match wins: Preprint, then Comment/Editorial/Letter,
then Review/Guideline, otherwise a peer-reviewed article. Records from
`manual_entries.json` are typed by the importer, which calls anything in a
supplement issue (S1, Suppl_1) or titled "Abstract ..." a conference abstract.
That is a guess. Check the `group` field after importing and correct it by
hand if needed; the file is small and hand-editable. To move something, change `GROUP_RULES` in
`fetch_pubmed.py` rather than editing the output.

### Lab member highlighting

Names in `lab_members.txt` render in blue on the publications page; the PI
renders in crimson. A legend at the top of the page says which is which. The
roster covers trainees and staff together. If you ever want them distinguished,
add a second colour and a second file rather than overloading the blue.

PubMed has no concept of a lab affiliation, so this roster is maintained by hand. One
name per line, either `Rogers EM` (exactly as PubMed prints it) or
`Emily Rogers`. Use the PubMed form for compound surnames: PubMed prints
`Lima Oliveira M`, so `Manoela Lima Oliveira` would look for `Oliveira ML` and
miss.

Matching is surname plus an initials prefix, so `Rogers E` in the roster
matches `Rogers EM` on a paper and vice versa. **That also means a common
surname can collide.** After editing the roster, run the build and read the
`lab roster` line plus the output — a co-author who happens to share a
surname with a trainee will be highlighted too.

Six names were confirmed directly by Nate on 2026-09-25. The rest were inferred
from first-authorship and are marked unconfirmed in the file.

### Byline

PubMed records his initials inconsistently across the years (`ND`, `NDM`, and
once just `N`). `build_publications.py` normalizes all of them to `Jenkins NDM`
and marks that author for highlighting. The variants are listed in
`PI_INITIAL_VARIANTS`.

### Known gaps

PubMed indexes biomedical literature only. Book chapters and anything in a
non-indexed journal reach the site through `manual_entries.json`, which means
they appear only if they are in your My Bibliography export. Nothing outside
both PubMed and My Bibliography will ever show up.

## Fonts

Both pages currently load Archivo, Source Serif 4, and JetBrains Mono from
Google Fonts. Consider self-hosting them in `Media/fonts/` instead: it removes
a third-party request on every page load, which some university privacy
policies prefer, and the pages keep their typography if Google is unreachable.

## Deploying

Settings → Pages → Build and deployment → Deploy from a branch → `main`, root.
The publications job needs Settings → Actions → General → Workflow permissions
set to "Read and write permissions" so it can commit what it regenerates.
