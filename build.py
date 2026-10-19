#!/usr/bin/env python3
"""Builds the Diamond Ranch Farmstead site into _site/.

No dependencies. Usage:
    python3 build.py                 # base path from SITE_BASE env (default "")
    SITE_BASE=/diamond-ranch-farmstead python3 build.py

Page sources live in src/pages/. Each starts with a small header:
    title: Page title
    description: Meta description
    path: /goats/
    ---
followed by HTML. Tokens like {{email}} come from site.json, and
<!-- render:NAME --> blocks are filled from data/animals.json.
"""
import hashlib
import html
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
SITE = json.loads((ROOT / "site.json").read_text())
DATA = json.loads((ROOT / "data" / "animals.json").read_text())
BASE = os.environ.get("SITE_BASE", "").rstrip("/")
CSS_VERSION = hashlib.md5((ROOT / "assets" / "style.css").read_bytes()).hexdigest()[:8]

STATUS_LABEL = {"available": "Available", "reserved": "Reserved", "sold": "Sold"}


def esc(value):
    return html.escape(str(value or ""))


def url(path):
    return BASE + path


def photo_or_mark(item, alt):
    if item.get("photo"):
        return (f'<img src="{url("/assets/img/" + item["photo"])}" alt="{esc(alt)}" '
                f'loading="lazy" width="800" height="600">')
    return (f'<div class="no-photo"><img src="{url("/assets/img/logo-240.webp")}" alt="" width="240" height="240">'
            '<span>Photo coming soon</span></div>')


def status_tag(item):
    status = item.get("status", "available")
    return f'<span class="status status-{esc(status)}">{STATUS_LABEL.get(status, esc(status))}</span>'


def render_parents():
    rows = []
    for dog in DATA.get("gampr_parents", []):
        rows.append(
            f'<li class="animal"><a class="animal-link" href="{url("/dogs/" + dog["slug"] + "/")}">'
            f'{photo_or_mark(dog, dog["name"] + ", Armenian Gampr")}'
            f'<div class="animal-text"><h3>{esc(dog["name"])}</h3>'
            f'<p>{esc(dog.get("health"))}</p><span class="row-link">Meet {esc(dog["name"])}</span></div></a></li>')
    return f'<ul class="animal-grid">{"".join(rows)}</ul>'


def fmt_date(iso):
    if not iso:
        return ""
    y, m, d = (int(x) for x in iso.split("-"))
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    return f"{months[m - 1]} {d}, {y}"


def pedigree_cells(node, gen, row, cells, max_gen=3):
    """Lay a pedigree out on a grid: gen 1..3 columns, 8 rows. Parent spans 4, grandparent 2."""
    span = 2 ** (max_gen - gen)
    role = "Sire" if (row // span) % 2 == 0 else "Dam"
    if node:
        reg = f'<span class="ped-reg">{esc(node["reg"])}</span>' if node.get("reg") else ""
        inner = f'<span class="ped-role">{role}</span><span class="ped-name">{esc(node["name"])}</span>{reg}'
        cls = "ped-cell"
    else:
        inner = ""
        cls = "ped-cell ped-empty"
    cells.append(f'<div class="{cls}" style="grid-column:{gen};grid-row:{row + 1} / span {span}">{inner}</div>')
    if gen < max_gen:
        half = span // 2
        pedigree_cells((node or {}).get("sire"), gen + 1, row, cells, max_gen)
        pedigree_cells((node or {}).get("dam"), gen + 1, row + half, cells, max_gen)


def render_pedigree(ped):
    if not any((ped.get(k) or {}).get("sire") or (ped.get(k) or {}).get("dam") for k in ("sire", "dam")):
        rows = []
        for role in ("sire", "dam"):
            node = ped.get(role)
            if node:
                reg = f'<span class="ped-reg">{esc(node["reg"])}</span>' if node.get("reg") else ""
                rows.append(f'<div class="ped-cell ped-parent"><span class="ped-role">{role.title()}</span>'
                            f'<span class="ped-name">{esc(node["name"])}</span>{reg}</div>')
        return f'<div class="ped-parents">{"".join(rows)}</div>'
    cells = []
    pedigree_cells(ped.get("sire"), 1, 0, cells)
    pedigree_cells(ped.get("dam"), 1, 4, cells)
    head = ('<div class="ped-head" style="grid-column:1">Parents</div>'
            '<div class="ped-head" style="grid-column:2">Grandparents</div>'
            '<div class="ped-head" style="grid-column:3">Great-grandparents</div>')
    return f'<div class="pedigree" role="table" aria-label="Pedigree">{head}<div class="ped-grid">{"".join(cells)}</div></div>'


def ext_link(href, label):
    return (f'<a class="ext-link" href="{esc(href)}" target="_blank" rel="noopener noreferrer">'
            f'{label}<span class="visually-hidden"> (opens in a new window)</span></a>')


def render_videos(vids):
    if not vids:
        return ""
    return '<div class="stop-videos">' + "".join(
        f'<figure><video controls playsinline preload="none" '
        f'poster="{url("/assets/img/" + esc(v["poster"]))}" aria-label="{esc(v.get("caption"))}">'
        f'<source src="{url("/assets/" + esc(v["src"]))}" type="video/mp4"></video>'
        f'<figcaption>{esc(v.get("caption", ""))}</figcaption></figure>' for v in vids) + "</div>"


def render_dog_litter(dog):
    lit = dog.get("litter")
    if not lit:
        return ""
    photos = DATA.get("past_litter_photos", [])
    items = "".join(
        f'<li><img src="{url("/assets/img/" + esc(p["photo"]))}" alt="{esc(p.get("alt"))}" loading="lazy" width="900" height="675"></li>'
        for p in photos)
    return (f'<section class="band" id="litter"><h2>{esc(lit["title"])}</h2><p>{esc(lit.get("text"))}</p>'
            f'{render_videos(lit.get("videos"))}<ul class="gallery litter-gallery">{items}</ul></section>')


def render_journey(dog):
    stops = dog.get("journey") or []
    if not stops:
        return ""
    items = []
    for i, stop in enumerate(stops, 1):
        media = ""
        if stop.get("photos"):
            media = '<ul class="stop-photos">' + "".join(
                f'<li><img src="{url("/assets/img/" + esc(ph["photo"]))}" alt="{esc(ph.get("alt"))}" loading="lazy"></li>'
                for ph in stop["photos"]) + "</ul>"
        vids = stop.get("videos") or ([stop["video"]] if stop.get("video") else [])
        if vids:
            media += '<div class="stop-videos">' + "".join(
                f'<figure><video controls playsinline preload="none" '
                f'poster="{url("/assets/img/" + esc(v["poster"]))}" aria-label="{esc(v.get("caption") or v.get("label"))}">'
                f'<source src="{url("/assets/" + esc(v["src"]))}" type="video/mp4"></video>'
                f'<figcaption>{esc(v.get("caption", ""))}</figcaption></figure>' for v in vids) + "</div>"
        items.append(
            f'<li class="stop"><span class="stop-num" aria-hidden="true">{i}</span>'
            f'<p class="stop-place">{esc(stop.get("place"))}</p><h3>{esc(stop.get("title"))}</h3>'
            f'<p>{esc(stop.get("text"))}</p>{media}</li>')
    return (f'<section class="band journey"><h2>{esc(dog["name"])}\'s journey</h2>'
            f'<p class="journey-route">{esc(dog.get("journey_intro", ""))}</p>'
            f'<ol class="stops">{"".join(items)}</ol></section>')


def dog_page(dog):
    name = dog["name"]
    facts = [("Registered name", esc(dog.get("registered_name"))),
             ("AGCA registration", esc(dog.get("reg"))),
             ("Sex", esc(dog.get("sex"))),
             ("Born", fmt_date(dog.get("born"))),
             ("Bred by", esc(dog.get("bred_by")))]
    facts_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts if v)
    links = []
    if dog.get("embark"):
        links.append(ext_link(dog["embark"], "Embark DNA profile"))
    if dog.get("ofa"):
        links.append(ext_link(dog["ofa"], "OFA health records"))
    if dog.get("agca"):
        links.append(ext_link(dog["agca"], "Breeder profile on Gampr.org"))
    links_html = f'<div class="ext-links">{"".join(links)}</div>' if links else ""
    gallery = dog.get("gallery") or []
    gal_html = ""
    if gallery:
        imgs = "".join(
            f'<li><img src="{url("/assets/img/" + esc(g["photo"]))}" alt="{esc(g.get("alt"))}" '
            f'loading="lazy" width="1200" height="900"></li>' for g in gallery)
        cls = f"count-{len(gallery)}" if len(gallery) <= 3 else "count-many"
        gal_html = f'<ul class="dog-gallery {cls}">{imgs}</ul>'
    ped = dog.get("pedigree") or {}
    ped_note = ""
    if not any((ped.get(k) or {}).get("sire") for k in ("sire", "dam")):
        ped_note = '<p class="ped-note">Her registration lists her parents only.</p>' if dog.get("sex") == "Female" \
            else '<p class="ped-note">His registration lists his parents only.</p>'
    body = f'''
<nav class="crumbs" aria-label="Breadcrumb"><a href="{url("/gampr-puppies/")}">Gampr puppies</a> <span aria-hidden="true">/</span> {esc(name)}</nav>
<section class="page-head dog-head">
  <h1>{esc(name)}</h1>
  <p class="dog-regname">{esc(dog.get("registered_name"))}</p>
  <p class="lede">{esc(dog.get("summary"))}</p>
  {"".join(f'<p class="dog-about">{esc(t)}</p>' for t in dog.get("about", []))}
</section>
<section class="band dog-photos">
  {gal_html}
</section>
{f'<section class="band"><h2>Videos</h2>{render_videos(dog.get("videos"))}</section>' if dog.get("videos") else ""}
{render_journey(dog)}
{render_dog_litter(dog)}
<section class="band two-col dog-info">
  <div>
    <h2>Registration</h2>
    <dl class="facts">{facts_html}</dl>
  </div>
  <div>
    <h2>Health testing</h2>
    <p>{esc(dog.get("health"))}</p>
    {links_html}
  </div>
</section>
<section class="band">
  <h2>Pedigree</h2>
  {ped_note}
  {render_pedigree(ped)}
</section>
<section class="band dog-cta">
  <p>Interested in a puppy from our program? <a class="button" href="{url("/gampr-puppies/")}#apply">Send a puppy application</a></p>
</section>'''
    meta = {"title": f"{name}, Armenian Gampr",
            "description": f"{name} ({dog.get('registered_name')}), an Armenian Gampr in the Diamond Ranch Farmstead breeding program in Hereford, Arizona. Photos, pedigree and health testing.",
            "path": f"/dogs/{dog['slug']}/", "slug": "dog", "section": "/gampr-puppies/"}
    return meta, body


def render_listing(key, empty_message, kind):
    items = DATA.get(key, [])
    if not items:
        return f'<div class="empty"><p>{empty_message}</p></div>'
    rows = []
    for item in items:
        facts = [item.get(f) for f in ("sex", "born", "registration") if item.get(f)]
        price = f'<p class="price">{esc(item["price"])}</p>' if item.get("price") else ""
        notes = f'<p>{esc(item["notes"])}</p>' if item.get("notes") else ""
        rows.append(
            f'<li class="animal">{photo_or_mark(item, item.get("name", kind))}'
            f'<div class="animal-text"><h3>{esc(item.get("name"))} {status_tag(item)}</h3>'
            f'<p class="facts">{esc(" · ".join(facts))}</p>{price}{notes}</div></li>')
    return f'<ul class="animal-grid">{"".join(rows)}</ul>'


def render_form(animal, hint="Acreage, livestock you need protected, fencing, experience with guardian dogs or goats, timing", ask="Tell us about your place and what you need"):
    return f'''
<form class="inquiry" action="https://formsubmit.co/{esc(SITE['email'])}" method="POST">
  <input type="hidden" name="_subject" value="Website inquiry: {esc(animal)}">
  <input type="hidden" name="_next" value="{esc(SITE['preview_url'] if SITE.get('preview') else SITE['url'])}{url('/thanks/')}">
  <input type="hidden" name="_template" value="table">
  <input type="hidden" name="Interested in" value="{esc(animal)}">
  <input type="text" name="_honey" class="honey" tabindex="-1" autocomplete="off" aria-hidden="true">
  <div class="field-row">
    <label>Your name<input name="Name" required autocomplete="name"></label>
    <label>Phone<input name="Phone" type="tel" autocomplete="tel"></label>
  </div>
  <label>Email<input name="email" type="email" required autocomplete="email"></label>
  <label>Where are you located?<input name="Location" placeholder="City and state"></label>
  <label>{esc(ask)}
    <textarea name="Message" rows="5" required placeholder="{esc(hint)}"></textarea>
  </label>
  <button type="submit">Send inquiry</button>
  <p class="form-note">We reply by email or phone.</p>
</form>'''


def render_gallery():
    photos = DATA.get("past_litter_photos", [])
    if not photos:
        return ""
    items = "".join(
        f'<li><img src="{url("/assets/img/" + esc(p["photo"]))}" alt="{esc(p.get("alt"))}" '
        f'loading="lazy" width="900" height="675"></li>' for p in photos)
    return (f'<section class="band"><h2>Puppies from Riley\'s first litter</h2>'
            f'<p>A few of the pups from Riley and Dozer\'s first litter, the same pairing planned for spring 2027. <a href="{url("/dogs/riley/")}#litter">See videos of the litter on Riley\'s page</a>.</p>'
            f'<ul class="gallery">{items}</ul></section>')


def render_planned():
    parents = {d["name"]: d for d in DATA.get("gampr_parents", [])}
    blocks = []
    for plan in DATA.get("planned_litters", []):
        pair = []
        for role, key in (("Sire", "sire"), ("Dam", "dam")):
            dog = parents.get(plan[key], {"name": plan[key]})
            pair.append(f'<figure>{photo_or_mark(dog, dog["name"] + ", Armenian Gampr")}'
                        f'<figcaption><strong>{esc(dog["name"])}</strong> {role}</figcaption></figure>')
        timing = f'<p class="planned-timing">{esc(plan["timing"])}</p>' if plan.get("timing") else ""
        note = f'<p>{esc(plan["note"])}</p>' if plan.get("note") else ""
        blocks.append(
            f'<div class="planned"><div class="planned-pair">{pair[0]}<span class="planned-x" aria-hidden="true">×</span>{pair[1]}</div>'
            f'<div class="planned-text"><h3>Planned litter: {esc(plan["sire"])} × {esc(plan["dam"])}</h3>{timing}{note}'
            f'<p>Meet both parents in Our breeding dogs below. Send an application to get on the waitlist for this litter, '
            f'and we\'ll contact you when puppies are on the way.</p>'
            f'<p><a class="button" href="#apply">Join the waitlist</a></p></div></div>')
    return "".join(blocks)


def render_litters():
    if DATA.get("gampr_litters") or not DATA.get("planned_litters"):
        return render_listing(
            "gampr_litters",
            "No litter is on the ground right now. Send an application below to join the waitlist "
            "for our next litter, and we'll contact you when puppies are expected.",
            "Gampr litter") + render_planned()
    return render_planned()


def render_home_next():
    plans = DATA.get("planned_litters", [])
    if not plans:
        return ""
    plan = plans[0]
    timing = f' {esc(plan["timing"])}.' if plan.get("timing") else ""
    return (f'<p class="next-litter"><span class="sil sil-gampr" aria-hidden="true"></span>'
            f'<span>Next planned litter: <strong>{esc(plan["sire"])} × {esc(plan["dam"])}</strong>.{timing} '
            f'<a href="{url("/gampr-puppies/")}#apply">Join the waitlist</a></span></p>')


def render_pets(key="pets"):
    rows = []
    for pet in DATA.get(key, []):
        photos = pet.get("photos") or []
        main = photo_or_mark(photos[0], photos[0].get("alt", pet["name"])) if photos else photo_or_mark({}, pet["name"])
        extra = ""
        if len(photos) > 1:
            extra = '<ul class="pet-more">' + "".join(
                f'<li><img src="{url("/assets/img/" + esc(ph["photo"]))}" alt="{esc(ph.get("alt"))}" loading="lazy"></li>'
                for ph in photos[1:]) + "</ul>"
        about = f'<p>{esc(pet["about"])}</p>' if pet.get("about") else ""
        rows.append(f'<li class="pet"><div class="pet-photo">{main}</div><div class="pet-text">'
                    f'<h3>{esc(pet["name"])}</h3>'
                    + (f'<p class="pet-kind">{esc(pet["kind"])}</p>' if pet.get("kind") else "")
                    + f'{about}{extra}{render_videos(pet.get("videos"))}</div></li>')
    return f'<ul class="pets">{"".join(rows)}</ul>'


def render_cats():
    cats = DATA.get("barn_cats") or {}
    about = f'<p>{esc(cats["about"])}</p>' if cats.get("about") else ""
    photos = cats.get("photos") or []
    if not photos:
        return about + '<div class="empty"><p>Barn cat photos coming soon.</p></div>'
    items = "".join(
        f'<li><img src="{url("/assets/img/" + esc(ph["photo"]))}" alt="{esc(ph.get("alt"))}" loading="lazy" width="900" height="675"></li>'
        for ph in photos)
    return about + f'<ul class="gallery">{items}</ul>'


RENDERERS = {
    "pets": render_pets,
    "horses": lambda: render_pets("horses"),
    "guardians": lambda: render_pets("guardians"),
    "cats": render_cats,
    "home-next": render_home_next,
    "gallery": render_gallery,
    "parents": render_parents,
    "litters": render_litters,
    "goats": lambda: render_listing(
        "goats",
        "No goats are listed right now. Ask about upcoming kids and we'll let you know what's coming.",
        "Nigerian Dwarf goat"),
    "sheep": lambda: render_listing(
        "sheep",
        "No sheep are listed right now. Ask about upcoming lambs and we'll let you know what's coming.",
        "Hair sheep"),
    "form-gampr": lambda: render_form("Gampr puppy"),
    "form-goats": lambda: render_form("Nigerian Dwarf goats"),
    "form-sheep": lambda: render_form("Hair sheep"),
    "form-general": lambda: render_form("General question"),
    "form-eggs": lambda: render_form("Delaware eggs", "Eating eggs or hatching eggs, how many dozen, and when you'd like them", "What would you like?"),
}


NAV = [
    ("/gampr-puppies/", "Gampr puppies"),
    ("/goats/", "Goats"),
    ("/sheep/", "Sheep"),
    ("/eggs/", "Eggs"),
    ("/ranch-life/", "Ranch life"),
    ("/about/", "About"),
    ("/contact/", "Contact"),
]


def parse_page(path):
    raw = path.read_text()
    head, body = raw.split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    return meta, body


def fill(text):
    text = re.sub(r"<!-- render:([\w-]+) -->", lambda m: RENDERERS[m.group(1)](), text)
    tokens = dict(SITE)
    tokens.update({f"link_{k}": v for k, v in SITE["links"].items()})
    tokens["base"] = BASE
    tokens["year"] = str(date.today().year)
    return re.sub(r"\{\{(\w+)\}\}", lambda m: esc(tokens[m.group(1)]), text)


def layout(meta, body):
    path = meta["path"]
    title = meta["title"] if path == "/" else f'{meta["title"]} | {SITE["name"]}'
    current = ' aria-current="page"'
    nav = "".join(
        f'<li><a href="{url(p)}"{current if p == meta.get("section", path) else ""}>{label}</a></li>'
        for p, label in NAV)
    robots = '<meta name="robots" content="noindex">' if SITE.get("preview") else ""
    banner = ('<div class="preview-banner">Preview of the new site. Not live yet.</div>'
              if SITE.get("preview") else "")
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": SITE["name"],
        "description": SITE["tagline"],
        "url": SITE["url"],
        "email": SITE["email"],
        "telephone": SITE["phone"],
        "address": {"@type": "PostalAddress", "addressLocality": "Hereford",
                    "addressRegion": "AZ", "addressCountry": "US"},
        "logo": SITE["url"] + "/assets/img/logo-240.png",
        "image": SITE["url"] + "/assets/img/og-image.jpg",
        "sameAs": list(SITE["links"].values()),
    }
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta["description"])}">
{robots}
<link rel="canonical" href="{SITE["url"]}{path}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(meta["description"])}">
<meta property="og:url" content="{SITE["url"]}{path}">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE["url"]}/assets/img/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#2b1a0e">
<link rel="icon" href="{url("/assets/favicon-32.png")}" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="{url("/assets/apple-touch-icon.png")}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rokkitt:wght@500;700;800&family=Libre+Franklin:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{url("/assets/style.css")}?v={CSS_VERSION}">
<script type="application/ld+json">{json.dumps(schema)}</script>
</head>
<body class="page-{meta.get("slug", "page")}">
{banner}
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <a class="brand" href="{url("/")}"><img src="{url("/assets/img/logo-240.webp")}" alt="" width="240" height="240"><span>Diamond Ranch Farmstead</span></a>
  <nav aria-label="Main"><ul>{nav}</ul></nav>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="herd" aria-hidden="true">
    <span class="sil sil-rooster"></span><span class="sil sil-hen"></span>
    <span class="herd-gap"></span>
    <span class="sil sil-saguaro"></span>
    <span class="herd-gap"></span>
    <span class="sil sil-sheep"></span><span class="sil sil-doe"></span><span class="sil sil-billy"></span>
    <span class="sil sil-gampr"></span>
  </div>
  <svg class="ridge" viewBox="0 0 1200 90" preserveAspectRatio="none" aria-hidden="true"><path d="M0 90V62l70-14 60 10 90-30 55 16 70-28 45 12 85-26 60 22 50-8 80 30 70-18 95 20 60-12 85 22 60-16 75 18 90-8V90Z"/></svg>
  <div class="footer-inner">
    <div>
      <img class="footer-logo" src="{url("/assets/img/logo-240.webp")}" alt="Diamond Ranch Farmstead logo" width="240" height="240" loading="lazy">
      <p class="footer-name">Diamond Ranch Farmstead</p>
      <p>{esc(SITE["owners"])}<br>Hereford, Arizona. Visits by appointment.</p>
    </div>
    <div>
      <p><a href="mailto:{esc(SITE["email"])}">{esc(SITE["email"])}</a><br>
      <a href="tel:{SITE["phone_link"]}">{esc(SITE["phone"])}</a></p>
    </div>
    <ul class="footer-links">
      <li><a href="{esc(SITE["links"]["facebook"])}">Facebook</a></li>
      <li><a href="{esc(SITE["links"]["instagram"])}">Instagram</a></li>
      <li><a href="{esc(SITE["links"]["youtube"])}">YouTube</a></li>
      <li><a href="{esc(SITE["links"]["agca"])}">AGCA breeder profile</a></li>
      <li><a href="{url("/terms-conditions/")}">Sales terms</a></li>
    </ul>
  </div>
  <p class="copyright">© {date.today().year} Diamond Ranch Farmstead</p>
</footer>
</body>
</html>
'''


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    pages = []
    for src in sorted((ROOT / "src" / "pages").glob("*.html")):
        meta, body = parse_page(src)
        meta["slug"] = src.stem
        page_html = layout(meta, fill(body))
        if meta["path"] == "/404/":
            target = OUT / "404.html"
        else:
            target = OUT / meta["path"].strip("/") / "index.html"
            if meta.get("sitemap", "yes") != "no":
                pages.append(meta["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html.replace('href=""', 'href="#"'))
    for dog in DATA.get("gampr_parents", []):
        meta, body = dog_page(dog)
        target = OUT / meta["path"].strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(layout(meta, body))
        pages.append(meta["path"])
    today = date.today().isoformat()
    sitemap = "".join(f"<url><loc>{SITE['url']}{p}</loc><lastmod>{today}</lastmod></url>" for p in pages)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sitemap}</urlset>\n')
    robots = "User-agent: *\nDisallow: /\n" if SITE.get("preview") else \
        f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n"
    (OUT / "robots.txt").write_text(robots)
    if not SITE.get("preview") and (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", OUT / "CNAME")
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(pages) + 1} pages into {OUT} (base: '{BASE}')")


if __name__ == "__main__":
    main()
