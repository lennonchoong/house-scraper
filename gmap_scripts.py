import requests
import json
from math import sin, cos, sqrt, atan2, radians

with open("./config.json") as f:
    config = json.load(f)


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


def search_closest_gyms(latitude, longitude):
    result = requests.get(
        f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude}%2C{longitude}&radius=2500&type=gym&key={config["GOOGLE_MAP_API_KEY"]}'
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


def add_distances_to_offices(entries):
    locations = [(x["latitude"], x["longitude"]) for x in entries]

    for i in range(0, len(locations), 10):
        loc_slice = locations[i : i + 10]
        for j, entry in enumerate(get_distances_to_office(loc_slice)):
            entries[i + j]["bloom_office_distance"] = entry["bloom_office_distance"]
            entries[i + j]["pltr_office_distance"] = entry["pltr_office_distance"]


def add_supermarket_and_gym(entries):
    for entry in entries:
        entry["supermarkets"] = search_closest_grocery_store(
            entry["latitude"], entry["longitude"]
        )
        # entry["gym"] = search_closest_gyms(entry["latitude"], entry["longitude"])
        del entry["latitude"]
        del entry["longitude"]