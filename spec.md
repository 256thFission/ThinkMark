# Project Specification: **docs‑llm‑scraper**

A hackathon‑friendly CLI that crawls documentation sites and outputs an **LLM‑ready package** containing a hierarchical map, cleaned markdown pages, and atomic RAG chunks, conforming to the emerging **llms.txt** convention.

---

## 1  Goals

- **Working prototype in ≤24 h**; correctness over cleverness.
- Accept a root URL + `config.json`, crawl & scrape with **Scrapy + BeautifulSoup4**, and export a self‑contained `docs‑llm‑pkg/` directory:
  - `manifest.json` – site tree
  - `pages/*.md` – normalized content
  - `chunks/*.json` – chunked RAG units
  - `assets/` – optional binaries
- Preserve logical hierarchy (navigation → manifest).
- Strip chrome (sidebars, headers, ads) and de‑duplicate repeated blocks.
- Produce deterministic, slug‑based filenames for reproducibility.

## 2  Non‑Goals

- Full MCP integration (stub hooks only).
- Advanced rate‑limiting, JavaScript rendering, or headless browsers.
- Perfect semantic chunking (simple heuristic is fine).

---

## 3  High‑Level Architecture

```text
╭─ CLI (Typer) ─────╮      ╭─ Exporter ───────────╮
│                   │      │   manifest.json      │
│  1. parse config  │──┬──►│   pages/*.md         │
│  2. launch spider │  │   │   chunks/*.json      │
╰───────────────────╯  │   ╰──────────────────────╯
                       │
╭──────── Scrapy Spider (HTML downloader) ───────╮
│  fetch → pass raw HTML                        │
╰───────────────────────────────────────────────╯
                       │
╭────── Cleaner (BeautifulSoup) ──────╮
│  remove noise, convert → Markdown   │
╰──────────────────────────────────────╯
```

---

## 4  Directory Layout
```text
docs‑llm‑pkg/
├─ manifest.json        # Section 6
├─ pages/               # Section 7
└─ chunks/              # Section 8
```
_Images and other binaries are **ignored** in this hackathon MVP; no `assets/` directory is generated._

---

## 5  Configuration (config.json)

Minimal yet extensible.

```json
{
  "start_url": "https://docs.example.com/",
  "allowed_domains": ["docs.example.com"],
  "include_paths": ["/api", "/guide"],
  "exclude_paths": ["/blog", "/changelog"],
  "remove_selectors": ["nav", ".sidebar", ".footer"],
  "max_depth": 4,
  "chunk": {
    "max_tokens": 2048,
    "overlap": 128
  }
}
```

Fields:

| Key                               | Type   | Purpose                                   |
| --------------------------------- | ------ | ----------------------------------------- |
| `start_url`                       | string | Entry point for crawl                     |
| `allowed_domains`                 | list   | Passed to Scrapy’s `allowed_domains`      |
| `include_paths` / `exclude_paths` | list   | Simple prefix filters                     |
| `remove_selectors`                | list   | CSS selectors stripped before markdownify |
| `max_depth`                       | int    | Crawl depth cap                           |
| `chunk`                           | object | Token‑based chunking params               |

---

## 6  manifest.json Schema (Hierarchical)

```jsonc
{
  "site": "Example Docs",
  "generated": "2025-04-19T14:00:00Z",
  "tree": {
    "title": "Home",
    "url": "https://…/",
    "page": "pages/index.md",
    "children": [
      {
        "title": "API",
        "url": "https://…/api",
        "page": "pages/api/index.md",
        "children": [
          {
            "title": "Users",
            "url": "https://…/api/users",
            "page": "pages/api/users.md"
          }
        ]
      },
      {
        "title": "Guides",
        "url": "https://…/guide",
        "page": "pages/guide/index.md"
      }
    ]
  }
}
```

- Fully nested `tree` mirrors the site’s navigation hierarchy.
- Omit `children` when a node is a leaf.  
- No flat `id`/`parent` arrays are used.

---

## 7  Page Normalization Rules
1. **HTML → Markdown** using [`markdownify`](https://github.com/matthewwithanm/python-markdownify).
2. Strip `remove_selectors`; fallback to `<main>`/`<article>` heuristics.
3. Preserve heading levels; convert code blocks with language hints.
4. Remove tracking query parameters from all outbound links.
5. **Skip images:** all `<img>` elements are dropped (alt text ignored for now).
6. **Deduplication:** SHA‑256 every paragraph; skip repeats found on ≥3 distinct pages.
7. **Complex tables / embeds:** replace with stub `> NOTE: table removed` and leave source URL.

---

## 8  Chunking Strategy

- Tokenize Markdown with `tiktoken` (`cl100k_base`).
- Sliding window:
  - `max_tokens` (default 2048) with `overlap` (default 128).
  - Split on nearest preceding heading; fallback to paragraph.
- Output JSON:

```json
{
  "id": "api_users--000",
  "page": "pages/api/users.md",
  "text": "…chunk body…",
  "tokens": 1894,
  "position": 0
}
```

File name: `<page‑slug>--NNN.json`.

---

## 9  CLI Interface

```
usage: docs‑llm‑scraper [OPTIONS] URL

Options:
  -c, --config PATH   Path to config.json (default: ./config.json)
  -o, --outdir PATH   Output directory (default: ./docs‑llm‑pkg)
  --resume            Continue an interrupted crawl
  -v, --verbose       Debug logging
```

Implementation: [`typer`](https://typer.tiangolo.com/) for zero‑boilerplate commands.

---

## 10  Dependencies

- Python ≥ 3.11 (f‑strings with |=, TOML built‑in).
- **Scrapy 2.x** – crawl orchestration.
- **BeautifulSoup4** – HTML cleaning.
- **markdownify** – HTML→MD.
- **tiktoken** – token counting.
- **Typer** – CLI.
- Packaging via **Poetry** (lock reproducible env).

---

## 11  Logging & Error Handling

- Use Python `logging` with levels DEBUG/INFO/WARN.
- Any non‑200 HTTP response stored in `logs/bad_urls.txt` and skipped.
- On unhandled exception, write traceback to `logs/crash.log`, then exit non‑zero.

---

## 12  Testing Strategy

- **Unit**: helper functions (slugify, markdownify wrapper, chunker).
- **Integration**: run crawler against local `tests/fixtures/site/` (static HTML) using `pytest‑docker`.
- CI: GitHub Actions „push“ → `pytest` + `ruff` linter.

---

## 13  Packaging & Distribution

- Single‑file executable via **PyInstaller** for easy install.
- Publish to PyPI post‑hackathon (optional).

---

## 14  Hackathon Milestones (≈48 h)

| Time    | Task                                    |
| ------- | --------------------------------------- |
| 0‑2 h   | Agree spec, set up repo + Poetry        |
| 2‑6 h   | Basic Scrapy spider → write to `pages/` |
| 6‑10 h  | Cleaner + markdownify                   |
| 10‑14 h | Chunker + tiktoken                      |
| 14‑18 h | Manifest builder                        |
| 18‑22 h | CLI polish + Typer                      |
| 22‑26 h | Config validation, error handling       |
| 26‑32 h | Dedup & asset handling                  |
| 32‑38 h | Tests + CI                              |
| 38‑44 h | PyInstaller bundle                      |
| 44‑48 h | Buffer / polish / demo prep             |

---

## 15  Future Roadmap (post‑hackathon)

1. **MCP Integration**
   - Expose `rag_search` tool powered by manifest+chunks.
   - Expose `page_fetch` tool returning full Markdown.
2. Generate `llms.txt` that enumerates URLs → chunk IDs.
3. Incremental crawl (Last‑Modified / ETag).
4. JS rendering via Playwright for SPA docs.
5. Semantic chunking using heading embeddings.

---

### Appendix A – llms.txt Quick Reference

> A plain‑text manifest at site root listing absolute URLs of pages that are safe for LLM ingestion. Our exporter emits `llms.txt` alongside `manifest.json` for hosting if desired.

```
# docs.example.com llms.txt (v0.2)
https://docs.example.com/api/users
https://docs.example.com/guide/intro
…
```

---

**End of Spec – v0.9 (2025‑04‑19)**

