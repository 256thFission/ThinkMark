# docs_llm_scraper/items.py
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
