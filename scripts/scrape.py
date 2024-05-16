#!/usr/bin/python
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta

import requests

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Define constants
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Content-Type': 'application/json',
    'lan': 'en',
    'deviceType': 'WEB',
    'Origin': 'https://bmtcwebportal.amnex.com',
    'Referer': 'https://bmtcwebportal.amnex.com/'
}
BASE_URL = 'https://bmtcmobileapistaging.amnex.com/WebAPI/'


# Function to fetch all routes
def get_routes():
    routes = []
    response = requests.post(f'{BASE_URL}GetAllRouteList', headers=HEADERS)
    with open("../data/raw/routes.json", "w") as f:
        f.write(response.text)
        routes = json.load(f)
    return routes


# Function to fetch route IDs and save them if necessary
def get_route_ids(routes):
    route_parents = {}

    logging.info("Fetching route IDs...")

    directory_path = "../data/raw/routeids"
    os.makedirs(directory_path, exist_ok=True)
    dir_list = set(os.listdir(directory_path))
    pending_routes = [route for route in routes['data'] if
                      (route['routeno'].replace(" UP", "").replace(" DOWN", "") + '.json') not in dir_list]

    routes_prefix = sorted(set(route['routeno'][:3] for route in pending_routes))

    for route_prefix in routes_prefix:
        if f'{route_prefix}.json' in dir_list:
            continue

        time.sleep(0.5)
        logging.debug(f"Fetching {route_prefix}.json")

        data = json.dumps({"routetext": route_prefix})
        response = requests.post(f'{BASE_URL}SearchRoute_v2', headers=HEADERS, data=data)

        with open(f'{directory_path}/{route_prefix}.json', 'w') as f:
            f.write(response.text)

    for filename in dir_list:
        with open(os.path.join(directory_path, filename), 'r', encoding='utf-8') as file:
            data = json.load(file)
            for route in data['data']:
                route_parents[route['routeno']] = route['routeparentid']

    logging.info("Finished fetching route IDs!")
    return route_parents


# Function to fetch route lines and save them
def get_route_lines(routes):
    logging.info("Fetching route lines...")

    directory_path = "../data/raw/routelines"
    os.makedirs(directory_path, exist_ok=True)
    dir_list = set(os.listdir(directory_path))

    for route in routes['data']:
        filename = f"{route['routeno']}.json"
        if filename in dir_list:
            continue

        time.sleep(0.5)
        logging.debug(f"Fetching {filename}")

        data = json.dumps({"routeid": route['routeid']})
        response = requests.post(f'{BASE_URL}RoutePoints', headers=HEADERS, data=data)

        with open(f'{directory_path}/{filename}', 'w') as f:
            f.write(response.text)
        logging.info(f"Fetched {filename}")

    logging.info(f"Finished fetching route lines... ({len(dir_list)} route lines)")


# Function to fetch timetables and save them
def get_timetables(routes):
    logging.info("Fetching timetables...")

    for day in range(1, 8):
        date = datetime.now() + timedelta(days=day)
        dow = date.strftime("%A")
        directory_path = f'../data/raw/timetables/{dow}'
        os.makedirs(directory_path, exist_ok=True)
        dir_list = set(os.listdir(directory_path))

        for route in routes['data']:
            filename = f"{route['routeno']}.json"
            if filename in dir_list:
                continue

            time.sleep(0.5)
            logging.debug(f"Fetching {filename}")

            data = json.dumps({
                "routeid": route['routeid'],
                "fromStationId": route['fromstationid'],
                "toStationId": route['tostationid'],
                "current_date": date.strftime("%Y-%m-%d")
            })
            response = requests.post(f'{BASE_URL}GetTimetableByRouteid_v2', headers=HEADERS, data=data)

            with open(f'{directory_path}/{filename}', 'w') as f:
                f.write(response.text)
            logging.info(f"Fetched {filename}")

        logging.info(f"Finished fetching timetables for {dow}... ({len(dir_list)} timetables)")


# Function to fetch stop lists and save them
def get_stop_lists(routes, route_parents):
    logging.info("Fetching stop lists...")

    directory_path = "../data/raw/stops"
    os.makedirs(directory_path, exist_ok=True)
    dir_list = set(os.listdir(directory_path))
    pending_routes = [route['routeno'] for route in routes['data'] if (route['routeno'] + '.json') not in dir_list]
    pending_routes.reverse()

    for attempt in range(1, 100):
        for route in pending_routes:
            routeparentname = route.replace(" UP", "").replace(" DOWN", "")
            try:
                if f'{route}.json' in dir_list:
                    continue

                time.sleep(0.5)
                logging.debug(f"Fetching {routeparentname}.json with route ID {route_parents[routeparentname]}")

                data = json.dumps({"routeid": route_parents[routeparentname], "servicetypeid": 0})
                response = requests.post(f'{BASE_URL}SearchByRouteDetails_v4', headers=HEADERS, data=data)
                response_data = response.json()

                if response_data.get("message") == "Data not found":
                    continue

                if response_data.get("up", {}).get("data"):
                    with open(f'{directory_path}/{routeparentname} UP.json', 'w') as f:
                        f.write(response.text)
                if response_data.get("down", {}).get("data"):
                    with open(f'{directory_path}/{routeparentname} DOWN.json', 'w') as f:
                        f.write(response.text)

                pending_routes.remove(route)
                logging.info(f"Fetched {routeparentname}.json with route ID {route_parents[routeparentname]}")
            except Exception:
                logging.error(f"Failed {routeparentname}.json")
                logging.error(traceback.format_exc())

    logging.info(f"Finished fetching stop lists ({len(dir_list)} routes)")


# Main workflow
if __name__ == "__main__":
    routes = get_routes()
    route_parents = get_route_ids(routes)
    get_route_lines(routes)
    get_timetables(routes)
    get_stop_lists(routes, route_parents)
