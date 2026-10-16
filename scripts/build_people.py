#!/usr/bin/env python3
"""
Build people.html from people.json.

Shares the VSPR design tokens with index.html and publications.html.

    python3 scripts/build_people.py
"""

import argparse
import html
import json
from pathlib import Path


def initials(name):
    parts = [p for p in name.replace("[PLACEHOLDER]", "").split() if p[:1].isalpha()]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def photo_html(p, big=False):
    cls = "portrait portrait-lg" if big else "portrait"
    if p.get("photo"):
        return ('<img class="%s" src="%s" alt="%s" loading="lazy">'
                % (cls, html.escape(p["photo"]), html.escape(p["name"])))
    # No photo yet: a monogram placeholder rather than a broken image.
    return '<div class="%s portrait-blank" aria-hidden="true">%s</div>' % (cls, initials(p["name"]))


def links_html(p):
    out = []
    if p.get("email"):
        e = html.escape(p["email"])
        out.append('<a href="mailto:%s">email</a>' % e)
    if p.get("scholar"):
        out.append('<a href="%s" rel="noopener">scholar</a>' % html.escape(p["scholar"]))
    if p.get("orcid"):
        o = html.escape(p["orcid"])
        out.append('<a href="https://orcid.org/%s" rel="noopener">orcid</a>' % o)
    return '<p class="person-links">%s</p>' % " ".join(out) if out else ""


def name_html(p):
    n = html.escape(p["name"])
    if p.get("credentials"):
        n += ', <span class="creds">%s</span>' % html.escape(p["credentials"])
    return n


def feature_card(p):
    # bio may be a string or a list of paragraphs; a long bio needs breaks.
    paras = p.get("bio") or []
    if isinstance(paras, str):
        paras = [paras]
    bio = "\n          ".join('<p class="person-bio">%s</p>' % html.escape(t) for t in paras)
    return (
        '<div class="feature">\n'
        '        %s\n'
        '        <div class="feature-body">\n'
        '          <h3 class="person-name">%s</h3>\n'
        '          <p class="person-role">%s</p>\n'
        '          %s\n'
        '          %s\n'
        '        </div>\n'
        '      </div>'
        % (photo_html(p, big=True), name_html(p),
           html.escape(p.get("role") or ""), bio, links_html(p))
    )


def card(p):
    b = p.get("bio") or []
    if isinstance(b, str):
        b = [b]
    bio = "".join('<p class="person-bio">%s</p>' % html.escape(t) for t in b)
    return (
        '<li class="person">\n'
        '          %s\n'
        '          <h3 class="person-name">%s</h3>\n'
        '          <p class="person-role">%s</p>\n'
        '          %s\n'
        '          %s\n'
        '        </li>'
        % (photo_html(p), name_html(p), html.escape(p.get("role") or ""), bio, links_html(p))
    )


def compact_row(p):
    """Alumni carry two facts: what they did here, and where they are now."""
    role = html.escape(p.get("role") or "")
    now = html.escape(p.get("now") or "")
    head = ('<div class="alum-head"><span class="alum-name">%s</span>'
            '<span class="alum-now">%s</span></div>' % (name_html(p), now or role))
    sub = '<p class="alum-role">%s</p>' % role if (now and role) else ""
    return '<li class="alum">%s%s</li>' % (head, sub)


def strip_placeholders(node):
    """Drop any field still holding scaffold text.

    A field reading "[PLACEHOLDER] ..." is a note to ourselves, not content.
    Removing it lets the templates fall back to their empty-field behaviour,
    so an unfinished bio or an unknown alumni destination simply does not
    render instead of announcing itself on a live page.
    """
    if isinstance(node, dict):
        return {k: strip_placeholders(v) for k, v in node.items()
                if not (isinstance(v, str) and v.lstrip().startswith("[PLACEHOLDER]"))}
    if isinstance(node, list):
        return [strip_placeholders(v) for v in node]
    return node


def build(data):
    blocks = []
    for g in data["groups"]:
        people = g.get("people") or []
        if not people:
            continue
        head = ('<div class="group-head">\n'
                '      <h2 class="group-title">%s</h2>\n' % html.escape(g["title"]))
        if g.get("blurb"):
            head += '      <p class="group-blurb">%s</p>\n' % html.escape(g["blurb"])
        head += '    </div>'

        if g.get("feature"):
            body = "\n      ".join(feature_card(p) for p in people)
        elif g.get("compact"):
            body = ('<ul class="alum-list">\n        '
                    + "\n        ".join(compact_row(p) for p in people)
                    + '\n      </ul>')
        else:
            body = ('<ul class="people-grid">\n        '
                    + "\n        ".join(card(p) for p in people)
                    + '\n      </ul>')

        blocks.append('<section class="group" id="%s">\n    %s\n      %s\n  </section>'
                      % (html.escape(g["id"]), head, body))
    return TEMPLATE.replace("{{SECTIONS}}", "\n\n  ".join(blocks))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>People &middot; VSPR Lab</title>
<meta name="description" content="People of the Vascular Stress Physiology and Resilience Laboratory at the University of Wisconsin-Madison.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#F8F8F8; --paper-deep:#EFEFF0; --ink:#1D1C1F; --slate:#6B6A70;
  --crimson:#B50811; --gold:#BF9B54; --blue:#2A5D8F;
  --display:"Archivo",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --body:"Source Serif 4",Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --gutter:clamp(20px,5vw,84px);
  --rule:1px solid rgba(29,28,31,.13);
}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);
  font-size:17px;line-height:1.62;-webkit-font-smoothing:antialiased}
img{max-width:100%;height:auto;display:block}

.masthead{border-bottom:var(--rule);padding:14px var(--gutter);display:flex;
  align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap}
.masthead-inst{font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.14em;
  text-transform:uppercase;color:var(--slate);margin:0}
.masthead-inst strong{color:var(--ink);font-weight:700}
.sitenav{display:flex;gap:18px;font-family:var(--mono);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase}
.sitenav a{color:var(--slate);text-decoration:none;padding-bottom:2px;border-bottom:1px solid transparent}
.sitenav a:hover{color:var(--ink);border-bottom-color:var(--gold)}
.sitenav a[aria-current="page"]{color:var(--crimson);border-bottom-color:var(--crimson)}
.hairline{height:2px;background:var(--gold);opacity:.85}

.pagehead{max-width:1440px;margin:0 auto;padding:clamp(40px,6vw,76px) var(--gutter) clamp(18px,3vw,30px)}
.pagehead h1{font-family:var(--display);font-weight:800;letter-spacing:-.035em;
  font-size:clamp(2.4rem,6.5vw,4.6rem);line-height:1;margin:0 0 1rem}
.pagehead p{color:var(--slate);max-width:60ch;margin:0}

.group{max-width:1440px;margin:0 auto;padding:0 var(--gutter) clamp(30px,5vw,58px)}
.group-head{border-top:2px solid var(--ink);padding-top:14px;margin-bottom:clamp(18px,3vw,30px)}
.group-title{font-family:var(--display);font-weight:700;font-size:clamp(1.25rem,2.4vw,1.7rem);
  letter-spacing:-.02em;margin:0}
.group-blurb{font-size:.94rem;color:var(--slate);margin:.3rem 0 0;max-width:56ch}

.portrait{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:2px;
  background:var(--paper-deep);filter:grayscale(1) contrast(1.02)}
.person:hover .portrait,.feature:hover .portrait{filter:none}
.portrait-lg{width:200px;flex:0 0 200px}
.portrait-blank{display:flex;align-items:center;justify-content:center;
  font-family:var(--display);font-weight:700;font-size:1.6rem;color:var(--slate);
  border:1px dashed var(--gold);filter:none}

.feature{display:flex;gap:clamp(20px,3vw,36px);flex-wrap:wrap;align-items:flex-start}
.feature-body{flex:1 1 320px;max-width:62ch}

.people-grid{list-style:none;margin:0;padding:0;display:grid;gap:clamp(22px,3vw,36px);
  grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}
.person{margin:0}

.person-name{font-family:var(--display);font-weight:700;font-size:1.06rem;
  letter-spacing:-.015em;margin:.7rem 0 .1rem}
.person-name .creds{font-family:var(--mono);font-size:.7em;font-weight:500;
  letter-spacing:.06em;color:var(--slate)}
.person-role{font-family:var(--mono);font-size:10.5px;letter-spacing:.11em;
  text-transform:uppercase;color:var(--crimson);margin:0 0 .5rem}
.person-bio{font-size:.95rem;color:var(--slate);margin:0 0 .85em}
.person-bio:last-of-type{margin-bottom:0}
.person-links{font-family:var(--mono);font-size:10px;letter-spacing:.11em;text-transform:uppercase;
  margin:.55rem 0 0;display:flex;gap:12px;flex-wrap:wrap}
.person-links a{color:var(--crimson);text-decoration:none;border-bottom:1px solid var(--gold)}
.person-links a:hover{border-bottom-color:var(--crimson)}

.alum-list{list-style:none;margin:0;padding:0;columns:2;column-gap:clamp(24px,4vw,56px)}
.alum{break-inside:avoid;padding:.5rem 0;border-bottom:var(--rule)}
.alum-head{display:flex;justify-content:space-between;gap:14px;align-items:baseline}
.alum-name{font-weight:600}
.alum-now{font-size:.9rem;color:var(--slate);text-align:right}
.alum-role{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--gold);margin:.15rem 0 0}
@media (max-width:700px){.alum-list{columns:1}}

.foot{border-top:var(--rule);padding:clamp(30px,4vw,48px) var(--gutter);max-width:1440px;
  margin:0 auto;display:flex;justify-content:space-between;gap:22px;flex-wrap:wrap;align-items:flex-end}
.foot-name{font-family:var(--display);font-weight:700;font-size:1.02rem;letter-spacing:-.01em;margin:0 0 .3rem}
.foot-meta{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--slate);margin:0;line-height:1.9}
.foot-meta a{color:var(--crimson);text-decoration:none;border-bottom:1px solid var(--gold)}
.foot-mark{width:118px;opacity:.5}
:where(a,button):focus-visible{outline:2px solid var(--crimson);outline-offset:3px;border-radius:2px}
</style>
</head>
<body>

<header class="masthead">
  <p class="masthead-inst"><strong>University of Wisconsin&ndash;Madison</strong> &middot; Department of Kinesiology</p>
  <nav class="sitenav">
    <a href="index.html">Home</a>
    <a href="lab.html">Lab</a>
    <a href="people.html" aria-current="page">People</a>
    <a href="publications.html">Publications</a>
  </nav>
</header>
<div class="hairline" role="presentation"></div>

<main>
  <div class="pagehead">
    <h1>People</h1>
    <p>The Vascular Stress Physiology and Resilience Laboratory.</p>
  </div>

  {{SECTIONS}}
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
  <img class="foot-mark" src="Media/vspr-monogram.png" alt="">
</footer>

</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="people.json")
    ap.add_argument("--out", default="people.html")
    args = ap.parse_args()
    data = strip_placeholders(json.loads(Path(args.data).read_text(encoding="utf-8")))
    Path(args.out).write_text(build(data), encoding="utf-8")
    n = sum(len(g.get("people") or []) for g in data["groups"])
    print("wrote %s with %d people" % (args.out, n))


if __name__ == "__main__":
    main()
