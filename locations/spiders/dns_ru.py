from locations.categories import Categories
from locations.structured_data_spider import StructuredDataSpider
from scrapy.spiders import SitemapSpider

from locations.user_agents import BROWSER_DEFAULT



class DnsRuSpider(SitemapSpider, StructuredDataSpider):
    name = "dns_ru"
    item_attributes = {"brand": "DNS", "brand_wikidata": "Q4036922", 'extras': Categories.SHOP_ELECTRONICS.value}
    user_agent = BROWSER_DEFAULT
    sitemap_urls = ['https://www.dns-shop.ru/shops1.xml']
    sitemap_rules = [("", "parse_sd")]
    custom_settings = {'ROBOTSTXT_OBEY': False, 'CONCURRENT_REQUESTS': 1}
    wanted_types = ['Place']
    download_delay = 0.5