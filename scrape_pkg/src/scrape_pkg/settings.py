# scrape_pkg/src/scrape_pkg/settings.py
"""
Project‑wide Scrapy settings.  Import and override from scrapy.cfg or the crawler.
"""
BOT_NAME = "scrape_pkg"

SPIDER_MODULES = ["scrape_pkg.spiders"]
NEWSPIDER_MODULE = "scrape_pkg.spiders"

ROBOTSTXT_OBEY = False
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 60 * 60     # 1 h

# Default depth; individual spiders may override via custom_settings
DEPTH_LIMIT = 3
DOWNLOAD_DELAY = 0.1
CONCURRENT_REQUESTS_PER_DOMAIN = 8

ITEM_PIPELINES = {
    "scrape_pkg.pipelines.html_saver.HtmlSaverPipeline": 200,
    "scrape_pkg.pipelines.hierarchy.HierarchyPipeline": 300,
}
