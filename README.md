# Diamond Ranch Farmstead website

The site for diamondranchfarmstead.com. Every push to `main` builds and publishes it automatically through GitHub Pages (see the Actions tab).

## Common updates

All animals live in one file: `data/animals.json`.

- **New litter, goat or sheep:** add an entry to `gampr_litters`, `goats` or `sheep`.
- **Reserved or sold:** change `"status"` to `"reserved"` or `"sold"`.
- **Photo:** put the image in `assets/img/` and set `"photo"` to its file name.

Example goat entry:

```json
{
  "name": "Willow",
  "sex": "Doe",
  "born": "Born March 2026",
  "registration": "ADGA registered",
  "price": "$450",
  "status": "available",
  "notes": "Dam is a strong milker. Disbudded.",
  "photo": "willow.jpg"
}
```

Contact details and social links are in `site.json`. Page text is in `src/pages/`.

## Build locally (optional)

```
python3 build.py
python3 -m http.server -d _site 8000
```

## Going live on the custom domain

1. In `site.json`, set `"preview": false`.
2. Settings → Pages → Custom domain: `diamondranchfarmstead.com`, then tick Enforce HTTPS once it's offered.
3. At GoDaddy DNS: A records for `@` → 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153; CNAME `www` → `bdavidgarcia83.github.io`.
