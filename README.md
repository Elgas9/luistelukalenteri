# Varauskalenteri — Espoo public skating schedule

A tiny, beginner-friendly project: it pulls this week's public skating
times ("yleisöluistelu") for Espoo's ice rinks and publishes them as one
simple webpage anyone can open — no login, no app, just a link.

**Live page (once set up):** `https://<your-github-username>.github.io/<repo-name>/`

## How it works

1. [`scrape.py`](scrape.py) calls the public JSON feed behind Espoo's ice
   rink booking system (`resurssivaraus.espoo.fi`) for all 7 rinks, keeps
   only the "Yleisöluistelu" (public skating) slots, and writes them out
   as [`docs/index.html`](docs/index.html).
2. [`.github/workflows/update.yml`](.github/workflows/update.yml) runs
   that script automatically every Monday morning, and commits the
   refreshed page.
3. GitHub Pages serves `docs/index.html` as a website.

On purpose, this is simple rather than perfect:
- It only shows the **current week** (Monday–Sunday), not future weeks.
- It refreshes **once a week**, not the instant Espoo changes something.
- If Espoo opens a brand-new rink, someone has to add its "resource ID"
  to the `RINKS` dictionary in `scrape.py` by hand.

## Running it yourself locally

```bash
python3 scrape.py
```

This writes/updates `docs/index.html`, which you can open directly in a
browser. No extra packages to install — it only uses Python's standard
library.

## One-time setup to publish it (GitHub Pages)

1. Create a free account at [github.com](https://github.com) if you
   don't have one.
2. Create a new **public** repository (e.g. named `luistelukalenteri`).
3. Push this project to it:
   ```bash
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git branch -M main
   git push -u origin main
   ```
4. In the repo on GitHub: **Settings → Actions → General → Workflow
   permissions** → select **"Read and write permissions"** → Save.
   (This lets the weekly job commit the updated page back to the repo.)
5. In the repo on GitHub: **Settings → Pages** → under "Build and
   deployment", set **Source: Deploy from a branch**, **Branch: main,
   folder: /docs** → Save.
6. GitHub will give you a URL like
   `https://<your-username>.github.io/<repo-name>/` — that's the link
   you share with anyone. It updates itself every Monday, or you can
   trigger a manual refresh any time from the repo's **Actions** tab
   (choose "Update skating schedule" → "Run workflow").
