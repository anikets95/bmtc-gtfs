#!/usr/bin/python
import json
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/scrape-debug.log"),
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

# Configure requests session with retries and connection pooling
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100)
session.mount('http://', adapter)
session.mount('https://', adapter)


# Function to fetch all routes
def get_routes():
    response = session.post(f'{BASE_URL}GetAllRouteList', headers=HEADERS)
    if response.status_code != 200:
        logging.error(f'Failed to get route list: {response.text}')
        return None
    with open("bmtc-data/raw/routes.json", "w") as f:
        f.write(response.text)
    return response.json()


# Function to fetch route IDs and save them if necessary
def get_route_ids():
    route_parents = {}

    logging.info("Fetching route IDs...")

    directory_path = "bmtc-data/raw/routeids"
    os.makedirs(directory_path, exist_ok=True)

    for possible_search in '0123456789abcdefghijklmnopqrstuvwxyz':

        logging.debug(f"Fetching {possible_search}.json")

        data = json.dumps({"routetext": possible_search})
        response = session.post(f'{BASE_URL}SearchRoute_v2', headers=HEADERS, data=data)

        if (response.json().get('Message') in ["No Records Found",
                                               "Object reference not set to an instance of an object."]
                or not response.json().get('Issuccess')):
            logging.error(f"No route records found in API call starting with {possible_search}")
        else:
            with open(f'{directory_path}/{possible_search}.json', 'w') as f:
                f.write(response.text)

    dir_list = set(os.listdir(directory_path))

    for filename in dir_list:
        with open(os.path.join(directory_path, filename), 'r', encoding='utf-8') as file:
            data = json.load(file)
            for route in data['data']:
                if route['routeno'] not in route_parents:
                    route_parents[route['routeno']] = route['routeparentid']

    logging.info("Finished fetching route IDs!")

    return route_parents


# Function to fetch a single route line
def fetch_route_line(route):
    directory_path = "bmtc-data/raw/routelines"
    filename = f"{route['routeno']}.json"

    logging.debug(f"Fetching route line : {filename}")

    data = json.dumps({"routeid": route['routeid']})
    response = session.post(f'{BASE_URL}RoutePoints', headers=HEADERS, data=data)

    if response.json().get('Message') == "No Records Found" or not response.json().get('Issuccess'):
        logging.error(f"No route line record found in API call for routeid : {route['routeid']} or route {filename}")
    else:
        with open(f'{directory_path}/{filename}', 'w') as file:
            file.write(response.text)

    logging.debug(f"Fetched route line : {filename}")


# Function to fetch route lines and save them
def get_route_lines(routes):
    logging.info("Fetching route lines...")

    directory_path = "bmtc-data/raw/routelines"
    os.makedirs(directory_path, exist_ok=True)
    dir_list = set(os.listdir(directory_path))

    pending_routes = [route for route in routes['data'] if route['routeno'] + '.json' not in dir_list]

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_route_line, route) for route in pending_routes]
        for future in as_completed(futures):
            future.result()

    logging.info("Finished fetching route lines...")


# Function to fetch a single timetable
def fetch_timetable(route, dow, date):
    directory_path = f'bmtc-data/raw/timetables/{dow}'
    filename = f"{route['routeno']}.json"

    logging.debug(f"Fetching timetable for route {filename} on {dow}")

    data = json.dumps({
        "routeid": route['routeid'],
        "fromStationId": route['fromstationid'],
        "toStationId": route['tostationid'],
        "current_date": date.strftime("%Y-%m-%d")
    })
    response = session.post(f'{BASE_URL}GetTimetableByRouteid_v2', headers=HEADERS, data=data)

    if response.json().get('Message') == "No Records Found" or not response.json().get('Issuccess'):
        logging.error(f"No timetable records found In API call for routeid {route['routeid']} "
                      f"/ route : {route['routeno']} between {route['fromstationid']} and {route['tostationid']}"
                      f" for date : {date.strftime('%Y-%m-%d')}")
        return
    else:
        with open(f'{directory_path}/{filename}', 'w') as file:
            file.write(response.text)

    logging.debug(f"Fetched timetable for route {filename} on {dow}")


def fetch_timetables_for_day(day, routes):
    date = datetime.now() + timedelta(days=day)
    dow = date.strftime("%A")

    logging.info(f"Fetching timetables for day of {dow}")

    directory_path = f'bmtc-data/raw/timetables/{dow}'
    os.makedirs(directory_path, exist_ok=True)
    dir_list = set(os.listdir(directory_path))
    pending_routes = [route for route in routes['data'] if route['routeno'] + '.json' not in dir_list]

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_timetable, route, dow, date) for route in pending_routes]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error fetching timetable for route: {e}")


# Function to fetch timetables and save them
def get_timetables(routes):
    logging.info("Fetching timetables...")

    for day in range(1, 8):
        fetch_timetables_for_day(day, routes)

    logging.info("Finished fetching timetables...")


# Function to fetch a single stop list
def fetch_stop_list(route, route_parent):
    directory_path = "bmtc-data/raw/stops"
    filename = f'{route}.json'

    logging.debug(f"Fetching Stops for {filename} with route ID {route}")

    data = json.dumps({"routeid": route_parent, "servicetypeid": 0})
    try:
        response = session.post(f'{BASE_URL}SearchByRouteDetails_v4', headers=HEADERS, data=data)
        response_data = response.json()
    except BaseException:
        logging.error(f"Error fetching Stops for route {route}")
        logging.error(traceback.format_exc())
        return

    if response_data.get("message") == "Data not found" or not response_data.get('issuccess'):
        logging.error(f"No stop list records found for Stops In API call for route {route_parent} / {route}")
        return
    else:
        if response_data.get("up", {}).get("data"):
            with open(f'{directory_path}/{route} UP.json', 'w') as f:
                f.write(response.text)
        if response_data.get("down", {}).get("data"):
            with open(f'{directory_path}/{route} DOWN.json', 'w') as f:
                f.write(response.text)

    logging.debug(f"Fetched {filename} with route ID {route_parent} / {route}")


# Function to fetch stop lists and save them
def get_stop_lists(routes, route_parents):
    logging.info("Fetching stop lists...")

    directory_path = "bmtc-data/raw/stops"
    os.makedirs(directory_path, exist_ok=True)
    dir_list = os.listdir(directory_path)
    route_list = set([route.replace(" UP.json", "").replace(" DOWN.json", "") for route in dir_list])

    pending_routes = set()
    for route in routes['data']:
        if route['routeno'].replace(" UP", "").replace(" DOWN", "") not in route_list:
            pending_routes.add(route['routeno'].replace(" UP", "").replace(" DOWN", ""))

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_stop_list, route,
                                   route_parents.get(route)) for route in pending_routes]
        for future in as_completed(futures):
            future.result()

    logging.info("Finished fetching stop lists...")

# Main workflow
def main():
    routes = get_routes()
    route_parents = get_route_ids()
    get_route_lines(routes)
    get_timetables(routes)
    get_stop_lists(routes, route_parents)


if __name__ == "__main__":
    main()
