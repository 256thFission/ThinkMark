# docs_llm_scraper/pipelines/html_saver.py
"""
Save raw HTML and an append‑only URL→file map.
"""
from pathlib import Path
import json
from datetime import datetime

from docs_llm_scraper.items import PageItem
from docs_llm_scraper.utils.url_utils import slugify_path


class HtmlSaverPipeline:
    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir or "output")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(output_dir=crawler.settings.get("OUTPUT_DIR"))

    # ---------- Scrapy hooks ----------
    def open_spider(self, spider):
        self.raw_dir = self.output_dir / "raw_html"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.map_fp = (self.output_dir / "urls_map.jsonl").open("a", encoding="utf‑8")

    def close_spider(self, spider):
        self.map_fp.close()

    def process_item(self, item: PageItem, spider):
        slug = slugify_path(item["url"]) + ".html"
        (self.raw_dir / slug).write_bytes(item["html"])

        self.map_fp.write(
            json.dumps(
                {
                    "url": item["url"],
                    "file": f"raw_html/{slug}",
                    "title": item["title"],
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            )
            + "\n"
        )
        return item
