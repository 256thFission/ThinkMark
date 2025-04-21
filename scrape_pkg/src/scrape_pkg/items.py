# scrape_pkg/src/scrape_pkg/items.py
"""
Scrapy Items.
"""
import scrapy


class PageItem(scrapy.Item):
    url = scrapy.Field()
    depth = scrapy.Field()
    parent = scrapy.Field()
    title = scrapy.Field()
    html = scrapy.Field()  # raw bytes
