import requests
import re
import json
from time import sleep
from bs4 import BeautifulSoup
from gmap_scripts import add_distances_to_offices, add_supermarket_and_gym
from sheets_scripts import write_to_sheet


class ListingLimitException(Exception):
    pass


class RightmoveScraper:
    def __init__(self, config, min_price, max_price, rule_set_filter):
        self.config = config
        self.MAX_PRICE = max_price
        self.MIN_PRICE = min_price
        self.rule_set_filter = rule_set_filter

    def get_sq_footage(self, sizings):
        for size in sizings:
            if size["unit"] == "sqft":
                return size["minimumSize"]
        return None

    def format_rightmove_url(self, index):
        return f'https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E93917&maxBedrooms={self.config["BEDROOMS"]}&minBedrooms={self.config["BEDROOMS"]}&maxPrice={self.MAX_PRICE}&minPrice={self.MIN_PRICE}&index={index}&propertyTypes=flat&mustHave=&dontShow=&furnishTypes=&keywords='

    def get_specific_listing(self, url):
        html_response = requests.get(url).text
        soup = BeautifulSoup(html_response, "html.parser")
        json_obj = None

        for script in soup.select("script"):
            string = script.string
            if string and "window.PAGE" in string:
                idx = string.index("{")
                json_str = re.sub("\s+", "", string[idx:])
                json_obj = json.loads(json_str)
                break

        if not json_obj:
            return None

        return {
            "id": json_obj["propertyData"]["id"],
            "address": re.sub(
                "([A-Z])", r" \1", json_obj["propertyData"]["address"]["displayAddress"]
            ),
            "link": url,
            "price": re.sub(
                r"[^0-9]", "", json_obj["propertyData"]["prices"]["secondaryPrice"]
            ),
            "price_per_person": round(
                int(
                    re.sub(
                        r"[^0-9]",
                        "",
                        json_obj["propertyData"]["prices"]["secondaryPrice"],
                    )
                )
                / self.config["BEDROOMS"],
                2,
            ),
            "latitude": json_obj["analyticsInfo"]["analyticsProperty"]["latitude"],
            "longitude": json_obj["analyticsInfo"]["analyticsProperty"]["longitude"],
            "postcode": json_obj["analyticsInfo"]["analyticsProperty"]["postcode"],
            "nearestStations": ", ".join(
                [
                    re.sub("([A-Z])", r" \1", x["name"])
                    + " - "
                    + str(round(x["distance"], 2))
                    + "miles"
                    for x in json_obj["propertyData"]["nearestStations"]
                ]
            ),
            "bedrooms": json_obj["propertyData"]["bedrooms"],
            "bathrooms": json_obj["propertyData"]["bathrooms"],
            "size": self.get_sq_footage(json_obj["propertyData"]["sizings"]),
        }

    def page_listings(self, index, existing_ids):
        res = requests.get(self.format_rightmove_url(index))

        if res.status_code != 200:
            raise ListingLimitException("Page does not exist")

        soup = BeautifulSoup(res.text, "html.parser")
        links = set(
            [
                f'https://www.rightmove.co.uk{a["href"]}'
                for a in soup.select(".propertyCard-link")
            ]
        )
        print("Rightmove links", links)
        result = []

        for link in links:
            if existing_ids and (
                link.lstrip("https://www.rightmove.co.uk/properties/").rstrip(
                    "#/?channel=RES_LET"
                )
                in existing_ids
            ):
                continue
            result.append(self.get_specific_listing(link))

        result = add_distances_to_offices(result)

        result = [entry for entry in result if self.rule_set_filter(entry)]

        add_supermarket_and_gym(result)

        return result

    def scrape(self, existing_ids):
        idx = 12
        while idx <= 12:
            try:
                listings = self.page_listings(idx, existing_ids)
                write_to_sheet(listings)
                idx += 12
                sleep(5)
            except ListingLimitException:
                break
