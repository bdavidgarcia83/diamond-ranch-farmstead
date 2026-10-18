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
        health = esc(dog.get("health"))
        if dog.get("link"):
            health = f'<a href="{esc(dog["link"])}">{health}</a>'
        rows.append(
            f'<li class="animal">{photo_or_mark(dog, dog["name"] + ", Armenian Gampr")}'
            f'<div class="animal-text"><h3>{esc(dog["name"])}</h3>'
            f'<p>{health}</p></div></li>')
    return f'<ul class="animal-grid">{"".join(rows)}</ul>'


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


def render_form(animal):
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
  <label>Tell us about your place and what you need
    <textarea name="Message" rows="5" required placeholder="Acreage, livestock you need protected, fencing, experience with guardian dogs or goats, timing"></textarea>
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
    return (f'<section class="band"><h2>Puppies from our last litter</h2>'
            f'<p>A few of the pups from our most recent litter.</p>'
            f'<ul class="gallery">{items}</ul></section>')


RENDERERS = {
    "gallery": render_gallery,
    "parents": render_parents,
    "litters": lambda: render_listing(
        "gampr_litters",
        "No litter is on the ground right now. Send an application below to join the waitlist "
        "for our next litter, and we'll contact you when puppies are expected.",
        "Gampr litter"),
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
}


NAV = [
    ("/gampr-puppies/", "Gampr puppies"),
    ("/goats/", "Goats"),
    ("/sheep/", "Sheep"),
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
        f'<li><a href="{url(p)}"{current if p == path else ""}>{label}</a></li>'
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
