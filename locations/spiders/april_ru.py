from typing import Iterable

import scrapy
from scrapy.http import Request

from locations.dict_parser import DictParser
from locations.settings import DEFAULT_PLAYWRIGHT_SETTINGS
from locations.user_agents import BROWSER_DEFAULT


class AprilRuSpider(scrapy.Spider):
    name = "april_ru"
    item_attributes = {"brand_wikidata": "Q114060847"}
    start_urls = ["https://web-api.apteka-april.ru/gis/cities?hasPharmacies=true"]
    # TODO: figure out how to get this to work - website uses fingerprinting
    custom_settings = {
        # "DOWNLOADER_MIDDLEWARES": DOWNLOADER_MIDDLEWARES | {
        #     'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': None
        # },
        "ROBOTSTXT_OBEY": False,
        # "REDIRECT_ENABLED": False,
    } | DEFAULT_PLAYWRIGHT_SETTINGS
    is_playwright_spider = True

    def start_requests(self) -> Iterable[Request]:
        yield scrapy.Request(
            url="https://web-api.apteka-april.ru/gis/cities?hasPharmacies=true",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Origin": "https://apteka-april.ru",
                "Referer": "https://apteka-april",
                "User-Agent": BROWSER_DEFAULT,
            },
        )

    def parse(self, response):
        print(response.text)
        cities = response.json()
        district_ids = set([cities["districtID"] for cities in cities])
        for district_id in district_ids:
            yield scrapy.Request(
                url=f"https://web-api.apteka-april.ru/pharmacies?districtID={district_id}",
                callback=self.parse_pharmacies,
            )

    def parse_pharmacies(self, response):
        for pharmacy in response.json():
            item = DictParser.parse(pharmacy)
            item["lat"], item["lon"] = pharmacy.get("coords", [None, None])
            self.crawler.stats.inc_value(f"april_ru/brands/{pharmacy.get('brandID')}")
            yield item
