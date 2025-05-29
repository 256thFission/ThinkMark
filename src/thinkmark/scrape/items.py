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

    def __repr__(self):
        # Only show a summary of the html field
        html_val = self.get('html', b'')
        html_summary = f'<{len(html_val)} bytes>' if html_val else '<empty>'
        # Show up to 5 fields, but summarize html
        fields = {k: v for k, v in self.items() if k != 'html'}
        fields['html'] = html_summary
        return f"PageItem({fields})"
