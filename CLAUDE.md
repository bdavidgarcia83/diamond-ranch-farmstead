# Notes for maintaining this site

- Static site, no dependencies. `python3 build.py` renders `src/pages/*.html` through the layout in `build.py` into `_site/`. The GitHub Action passes the Pages base path as `SITE_BASE`; always link with `{{base}}` in page sources.
- Animals: `data/animals.json` only. Listing pages show an empty-state message when a list is empty. `planned_litters` drives the planned-litter block on the Gampr page and the "Next planned litter" line on the home page.
- Forms post to FormSubmit (formsubmit.co) at the farm email; no key needed. The first submission triggers an activation email to that inbox.
- `site.json` `"preview": true` adds a banner, `noindex` and a disallow-all robots.txt. Set false at launch.
- Owner's Terms page has `<mark class="todo">` items awaiting their answers; never invent policy (deposit amounts, guarantees).
- Never state facts about the animals (sex, ages, prices, test results) the owners haven't given.
- Design: colors come from the ranch logo (assets/img/logo-*.webp, source in Dropbox /Personal/Diamond Ranch Farmstead/Website/drflofo.jpg): sand bg, dark wood ink, rust accent. Rokkitt + Libre Franklin. Logo appears in header, hero, footer, favicon and og-image. Ranch silhouettes (assets/img/sil/, used as CSS masks via .sil classes) mark the home animal rows and walk along the footer ridge. Avoid cards/gradients.
- Commit as small, plainly described changes; push to `main` publishes.
