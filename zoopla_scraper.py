import json
import requests
from bs4 import BeautifulSoup
from sheets_scripts import write_to_sheet
from time import sleep
import subprocess
from gmap_scripts import add_distances_to_offices, add_supermarket_and_gym


class ListingLimitException(Exception):
    pass


class ZooplaScraper:
    def __init__(self, config, min_price, max_price, rule_set_filter):
        self.config = config
        self.MAX_PRICE = max_price
        self.MIN_PRICE = min_price
        self.rule_set_filter = rule_set_filter

    def format_zoopla_url(self, index):
        return f'https://www.zoopla.co.uk/to-rent/flats/london/?beds_max={self.config["BEDROOMS"]}&beds_min=${self.config["BEDROOMS"]}&price_frequency=per_month&price_max={self.MAX_PRICE}&price_min={self.MIN_PRICE}&property_sub_type=flats&q=London&search_source=refine'

    def get_specific_listing(self, url):
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        json_obj = None
        for s in soup.select("script"):
            if str(s).startswith('<script id="__NEXT_DATA__"'):
                json_obj = json.loads(str(s.find(text=True)))

        if not json_obj:
            return None

        listing_deets = json_obj["props"]["pageProps"]["listingDetails"]

        return {
            "id": listing_deets["listingId"] + "_z",
            "address": listing_deets["adTargeting"]["displayAddress"],
            "link": url,
            "price": listing_deets["pricing"]["alternateRentFrequencyPrice"][
                "internalValue"
            ],
            "price_per_person": listing_deets["pricing"]["alternateRentFrequencyPrice"][
                "internalValue"
            ]
            / self.config["BEDROOMS"],
            "latitude": listing_deets["location"]["coordinates"]["latitude"],
            "longitude": listing_deets["location"]["coordinates"]["longitude"],
            "postcode": listing_deets["adTargeting"]["outcode"]
            + " "
            + listing_deets["adTargeting"]["incode"],
            "nearestStations": ", ".join(
                [
                    f'{x["title"]} - {x["distanceMiles"]}miles'
                    for x in listing_deets["pointsOfInterest"]
                    if x["type"] in ["london_underground_station", "national_rail_station"]
                ]
            ),
            "bedrooms": listing_deets["adTargeting"]["numBeds"],
            "bathrooms": listing_deets["adTargeting"]["numBaths"],
            "size": listing_deets["adTargeting"]["sizeSqFeet"],
        }

    def page_listings(self, existing_ids):
        output = subprocess.check_output([
            'node', 'zoopla_scraper.js'
        ], timeout=60000)

        links = set(json.loads(output))

        result = [self.get_specific_listing(url) for url in links]

        add_distances_to_offices(result)

        result = [entry for entry in result if self.rule_set_filter(entry)]

        add_supermarket_and_gym(result)

        return result

    def scrape(self, existing_ids):
        # idx = 1
        # while idx <= 1:
        #     try:
        listings = self.page_listings(existing_ids)
        write_to_sheet(listings)
            #     idx += 1
            #     sleep(5)
            # except ListingLimitException:
            #     break