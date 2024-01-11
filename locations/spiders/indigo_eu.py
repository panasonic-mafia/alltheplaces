import csv
from datetime import datetime, timedelta
from typing import Iterable
from urllib.parse import urlencode, urljoin

import scrapy
from scrapy.http import Request

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.dict_parser import DictParser
from locations.searchable_points import open_searchable_points

# A spider for the Indigo parkings in Europe: https://www.indigoneo.com/en
# API docs: https://developer.opngo.com/api/reference
# At 2024-01-11 the data in this API is available for 'BE', 'CH', 'ES', 'FR', 'LU'.
# The data overlaps a bit with indigo.py spider, but we mostly get new POIs.


AMENITIES_MAPPING = {
    "DISABLED_ACCESS": Extras.PARKING_WHEELCHAIR,
    "TOILETS": Extras.TOILETS,
    "WIFI": Extras.WIFI,
    "CAR_WASH": Extras.CAR_WASH,
    "EV_CHARGING": "capacity:charging",
    # TODO: map below
    "GAS_STATION": None,
    "VEHICLE_SERVICING": None,
    "TYRE_INFLATION": None,
    "CAR_RENTAL": None,
    "BICYCLE_RENTAL": None,
    "SCOOTER_RENTAL": None,
    "MOTO_HELMETS": None,
    "FAMILY": None,
    "UMBRELLAS": None,
    "SECURITY_CAMERAS": None,
}


class IndigoEUSpider(scrapy.Spider):
    name = "indigo_eu"
    allowed_domains = ["api.opngo.com"]
    item_attributes = {"operator": "Indigo", "operator_wikidata": "Q3559970"}
    custom_settings = {"ROBOTSTXT_OBEY": False}
    download_delay = 1
    base_url = "https://api.opngo.com/quotes"
    headers = {"X-Api-Key": "QqdFIYjcqh5HK1EWHzdSH28Q3AvzoCHkY4cYMKM2"}

    def start_requests(self) -> Iterable[Request]:
        countries = ["BE", "CH", "ES", "FR", "LU"]
        with open_searchable_points("eu_centroids_120km_radius_country.csv") as points:
            for point in csv.DictReader(points):
                if point["country"] in countries:
                    # API needs start and end date/time. Use today's date/time, end time is 30 mins later,
                    # the API will give us all parkigs even if they are not available at given date/time.
                    start_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    end_time = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
                    lat, lon = point["latitude"], point["longitude"]
                    query = {
                        "latitude": lat,
                        "longitude": lon,
                        "radius": "120000",
                        "localStartTime": start_time,
                        "localEndTime": end_time,
                        "page": "0",
                        "pageSize": "500",
                    }

                    yield Request(
                        url=urljoin(self.base_url, "?" + urlencode(query)),
                        headers=self.headers,
                        meta=query,
                    )

    def parse(self, response):
        data = response.json()
        if records := data["content"]:
            for record in records:
                asset = record["asset"]
                asset.update(asset.pop("location", {}))
                item = DictParser.parse(asset)
                item["name"] = asset["assetName"]
                apply_category(Categories.PARKING, item)

                for amenity in asset.get("amenities", []):
                    if tag := AMENITIES_MAPPING.get(amenity):
                        apply_yes_no(tag, item, True)
                # TODO: opening hours are available at https://api.opngo.com/asset/793,
                #       but it requires extra API call.
                yield item

            if not data.get("lastPage"):
                meta = response.meta
                meta["page"] = int(meta["page"]) + 1
                yield Request(
                    url=urljoin(self.base_url, "?" + urlencode(meta)),
                    headers=self.headers,
                    meta=meta,
                    callback=self.parse,
                )
