# Notes for maintaining this site

- Static site, no dependencies. `python3 build.py` renders `src/pages/*.html` through the layout in `build.py` into `_site/`. The GitHub Action passes the Pages base path as `SITE_BASE`; always link with `{{base}}` in page sources.
- Animals: `data/animals.json` only. Listing pages show an empty-state message when a list is empty.
- Forms post to FormSubmit (formsubmit.co) at the farm email; no key needed. The first submission triggers an activation email to that inbox.
- `site.json` `"preview": true` adds a banner, `noindex` and a disallow-all robots.txt. Set false at launch.
- Owner's Terms page has `<mark class="todo">` items awaiting their answers; never invent policy (deposit amounts, guarantees).
- Never state facts about the animals (sex, ages, prices, test results) the owners haven't given.
- Design: high-desert palette in `assets/style.css` (sage bg, slate ink, ochre accent), Rokkitt + Libre Franklin, diamond-R brand mark. Avoid cards/gradients.
- Commit as small, plainly described changes; push to `main` publishes.
