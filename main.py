import json
from sheets_scripts import get_listing_ids
from rightmove_scraper import RightmoveScraper
from zoopla_scraper import ZooplaScraper

with open("./config.json") as f:
    config = json.load(f)

MIN_PRICE = int(round(config["MIN_PRICE"] * config["BEDROOMS"] * 4.4, -2))
MAX_PRICE = int(round(config["MAX_PRICE"] * config["BEDROOMS"] * 4.4, -2))


def rule_set_filter(entry):
    if (
        (
            float(entry["bloom_office_distance"].rstrip(" km"))
            + float(entry["pltr_office_distance"].rstrip(" km"))
        )
        / 2
    ) > config["MAX_DIST_TO_OFFICES"]:
        # print(
        #     f'EXCEEDING MAX DIST TO OFFICE: {(float(entry["bloom_office_distance"].rstrip(" km")) + float(entry["pltr_office_distance"].rstrip(" km"))) / 2}'
        # )
        return False

    if entry["bathrooms"] and entry["bathrooms"] < config["BATHROOMS"]:
        # print("BELOW MIN BATHROOMS")
        return False

    return True


if __name__ == "__main__":
    print(
        f'SEARCHING FOR HOUSES WITH {config["BEDROOMS"]} BEDROOMS FROM PRICES {MIN_PRICE}GBP - {MAX_PRICE}GBP ON RIGHTMOVE.CO.UK'
    )
    existing_ids = get_listing_ids()
    rightmove_scraper = RightmoveScraper(
        config=config,
        min_price=MIN_PRICE,
        max_price=MAX_PRICE,
        rule_set_filter=rule_set_filter,
    )
    rightmove_scraper.scrape(existing_ids)

    print(
        f'SEARCHING FOR HOUSES WITH {config["BEDROOMS"]} BEDROOMS FROM PRICES {MIN_PRICE}GBP - {MAX_PRICE}GBP ON ZOOPLA.COM'
    )
    rightmove_scraper = ZooplaScraper(
        config=config,
        min_price=MIN_PRICE,
        max_price=MAX_PRICE,
        rule_set_filter=rule_set_filter,
    )
    rightmove_scraper.scrape(existing_ids)