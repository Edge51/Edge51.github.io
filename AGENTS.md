# AGENTS.md

## Project Overview

**GitHub Pages** site using **Jekyll** (Minimal Mistakes theme). Blog site with sharable content only.

Custom domain: `blog.edge5134.com` (configured via `CNAME` + `_config.yml` `url`).

## Jekyll Site

```bash
bundle install                    # install deps (once)
bundle exec jekyll serve          # serve with live reload
bundle exec jekyll serve --config _config.yml,_config.dev.yml  # dev mode (localhost, no analytics)
bundle clean && bundle exec jekyll build  # clean rebuild
```

**Gotchas:**
- `_config.yml` is **NOT** reloaded during `jekyll serve` — restart server after edits.
- `_config.yml` has `future: true` — posts with future dates appear on the site.
- Delete `Gemfile.lock` if dependency conflicts arise, then `bundle install`.
- `CNAME` = `blog.edge5134.com` — do NOT delete or modify without DNS change.

## Content Structure

| Directory | Purpose | Edit frequency |
|-----------|---------|----------------|
| `_posts/` | Blog posts (markdown) | Regular |
| `_portfolio/` | Portfolio projects | Rare |
| `_publications/` | Publications list | Rare |
| `_talks/` | Talks list | Rare |
| `_data/` | YAML navigation/config files | Rare |

## Deployment

- **Method**: GitHub Pages (auto-build on push to `main`).
- **No local build needed** — GitHub builds the Jekyll site.
- `_site/` is gitignored (build artifact).

## Style & Conventions

- Posts are markdown with YAML frontmatter. No `.html` files in `_posts/`.
- `_config.dev.yml` overrides `url` to `localhost:4000` and disables analytics — use for local dev.
