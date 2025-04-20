# docs_llm_scraper/settings.py
"""
Project‑wide Scrapy settings.  Import and override from scrapy.cfg or the crawler.
"""
BOT_NAME = "docs_llm_scraper"

SPIDER_MODULES = ["docs_llm_scraper.spiders"]
NEWSPIDER_MODULE = "docs_llm_scraper.spiders"

ROBOTSTXT_OBEY = False
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 60 * 60     # 1 h

# Default depth; individual spiders may override via custom_settings
DEPTH_LIMIT = 4
DOWNLOAD_DELAY = 0.1
CONCURRENT_REQUESTS_PER_DOMAIN = 8

ITEM_PIPELINES = {
    "docs_llm_scraper.pipelines.html_saver.HtmlSaverPipeline": 200,
    "docs_llm_scraper.pipelines.hierarchy.HierarchyPipeline": 300,
}
