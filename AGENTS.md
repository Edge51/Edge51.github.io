# AGENTS.md

## Project Overview

This is a **GitHub Pages** site using **Jekyll** (Minimal Mistakes theme). The root is the main site; `trading-tools/` is a separate Python CLI subproject.

## Development Commands

### Jekyll Site (Root)

```bash
# Install dependencies (run once after clone/pull)
bundle install

# Serve locally (rebuilds on change)
bundle exec jekyll serve

# Use dev config (localhost, disabled analytics)
bundle exec jekyll serve --config _config.yml,_config.dev.yml

# Clean and rebuild
bundle clean && bundle exec jekyll build
```

- **URL**: Configured in `_config.yml` as `url: https://blog.edge5134.com`
- **Baseurl**: Empty (served from root)

### Trading Tools (Python CLI)

```bash
cd trading-tools

# Install dependencies
pip install -r requirements.txt

# Run CLI
python main.py --help

# Example commands
python main.py fetch-market --date 2026-05-12
python main.py full-review --date 2026-05-12
```

## Content Structure

| Directory | Purpose |
|-----------|---------|
| `_posts/` | Blog posts (markdown) |
| `_portfolio/` | Portfolio projects |
| `_publications/` | Publications list |
| `_talks/` | Talks list |
| `_readings/` | Reading notes |
| `_data/` | YAML data files for navigation/config |
| `trading-tools/` | Python trading tools (separate project) |

## Deployment

- **Method**: GitHub Pages (push to `main`/`master`)
- **Source**: Branch `gh-pages` or `main` with GitHub Actions (check repo settings)
- No local build step required for deployment; GitHub builds automatically.

## Notes

- `_config.yml` is NOT reloaded during `jekyll serve`. Restart server after edits.
- Delete `Gemfile.lock` if you encounter dependency conflicts, then re-run `bundle install`.
- The trading tools are independent of the Jekyll site—no shared build pipeline.