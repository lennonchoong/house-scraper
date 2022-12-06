import requests
import re
import json
from bs4 import BeautifulSoup
import pprint
from math import sin, cos, sqrt, atan2, radians
from itertools import filterfalse
import os.path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

with open("./config.json") as f:
    config = json.load(f)

MIN_PRICE = int(round(config["MIN_PRICE"] * config["BEDROOMS"] * 4.4, -2))
MAX_PRICE = int(round(config["MAX_PRICE"] * config["BEDROOMS"] * 4.4, -2))

rightmove_url = requests.get(
    f"https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E93917&maxBedrooms=2&minBedrooms=2&maxPrice={MAX_PRICE}&minPrice={MIN_PRICE}&index=12&propertyTypes=flat&mustHave=&dontShow=&furnishTypes=&keywords="
).text

creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file(
        "token.json", ["https://www.googleapis.com/auth/spreadsheets"]
    )


def get_sq_footage(sizings):
    for size in sizings:
        if size["unit"] == "sqft":
            return size["minimumSize"]
    return None


def get_specific_listing(url):
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
        "size": get_sq_footage(json_obj["propertyData"]["sizings"]),
    }


def get_distances_to_office(origins):
    office_locations = config["OFFICE_LOCATIONS"]
    destination_string = "%7C".join([f"{x[0]}%2C{x[1]}" for x in office_locations])
    origin_string = "%7C".join([f"{x[0]}%2C{x[1]}" for x in origins])
    result = requests.get(
        f'https://maps.googleapis.com/maps/api/distancematrix/json?destinations={destination_string}&origins={origin_string}&mode=transit&key={config["GOOGLE_MAP_API_KEY"]}'
    ).json()
    rows = result["rows"]
    aggregate = []
    for row in rows:
        bloom_office, pltr_office = row["elements"]
        aggregate.append(
            {
                "bloom_office_distance": bloom_office["distance"]["text"],
                "pltr_office_distance": pltr_office["distance"]["text"],
            }
        )
    return aggregate


def search_closest_grocery_store(latitude, longitude):
    result = requests.get(
        f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude}%2C{longitude}&radius=2500&type=supermarket&key={config["GOOGLE_MAP_API_KEY"]}'
    )

    arr = []
    for entry in result.json()["results"]:
        arr.append(
            (
                entry["name"],
                haversine_dist(
                    latitude,
                    longitude,
                    entry["geometry"]["location"]["lat"],
                    entry["geometry"]["location"]["lng"],
                ),
            )
        )

    arr.sort(key=lambda x: x[1])

    return ", ".join([f"{x[0]} - {x[1]}km" for x in arr[:8]])


def haversine_dist(lat1, lon1, lat2, lon2):
    R = 6373.0
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return round(distance, 1)


def page_listings(existing_ids):
    soup = BeautifulSoup(rightmove_url, "html.parser")
    links = set(
        [
            f'https://www.rightmove.co.uk{a["href"]}'
            for a in soup.select(".propertyCard-link")
        ]
    )
    result = []

    for link in links:
        if existing_ids and (
            link.lstrip("https://www.rightmove.co.uk/properties/").rstrip(
                "#/?channel=RES_LET"
            )
            in existing_ids
        ):
            continue
        result.append(get_specific_listing(link))
    locations = [(x["latitude"], x["longitude"]) for x in result]

    for i in range(0, len(locations), 10):
        loc_slice = locations[i : i + 10]
        for j, entry in enumerate(get_distances_to_office(loc_slice)):
            result[i + j]["bloom_office_distance"] = entry["bloom_office_distance"]
            result[i + j]["pltr_office_distance"] = entry["pltr_office_distance"]

    result = list(
        filterfalse(
            lambda entry: (
                (
                    float(entry["bloom_office_distance"].rstrip(" km"))
                    + float(entry["pltr_office_distance"].rstrip(" km"))
                )
                / 2
            )
            > config["MAX_DIST_TO_OFFICES"],
            result,
        )
    )

    for entry in result:
        entry["supermarkets"] = search_closest_grocery_store(
            entry["latitude"], entry["longitude"]
        )
        del entry["latitude"]
        del entry["longitude"]

    return result


def write_to_sheet(listings):
    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        rows = [list(row.values()) for row in listings]
        service.spreadsheets().values().append(
            spreadsheetId=config["SPREADSHEET_ID"],
            range="Sheet1!A:Z",
            body={"majorDimension": "ROWS", "values": rows},
            valueInputOption="USER_ENTERED",
        ).execute()
    except HttpError as err:
        print(err)


def get_listing_ids():
    try:
        service = build("sheets", "v4", credentials=creds)
        existing_ids = set()
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=config["SPREADSHEET_ID"], range="A1:A")
            .execute()
        )
        values = result.get("values", [])
        existing_ids.update([x[0] for x in values[1:]])
        return existing_ids
    except HttpError as err:
        print(err)


if __name__ == "__main__":
    print(
        f'SEARCHING FOR HOUSES WITH {config["BEDROOMS"]} BEDROOMS FROM PRICES {MIN_PRICE}GBP - {MAX_PRICE}GBP ON RIGHTMOVE.CO.UK'
    )
    existing_ids = get_listing_ids()
    listings = page_listings(existing_ids)
    write_to_sheet(listings)