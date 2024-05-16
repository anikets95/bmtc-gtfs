import datetime
import json
import logging
import os
import traceback

import transitfeed

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

schedule = transitfeed.Schedule()


def add_agency():
    schedule.AddAgency("BMTC", "https://mybmtc.karnataka.gov.in/english", "Asia/Kolkata", agency_id=1)


def add_service_period():
    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetStartDate("20230101")
    service_period.SetEndDate("20280101")
    service_period.SetWeekdayService(True)


def add_stops():
    directory = '../raw/stops/'
    stops = {}
    added_routes_stops = []
    failed_routes_stops = []

    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            if os.path.getsize(file_path) > 0:  # Check if file is not empty
                try:
                    with open(file_path, 'r') as file:
                        data = json.load(file)
                        for stop in (data.get("up", {}).get("data", []) + data.get("down", {}).get("data", [])):
                            if stop["stationid"] not in stops:
                                stops[stop["stationid"]] = schedule.AddStop(
                                    lng=stop["centerlong"], lat=stop["centerlat"], name=stop["stationname"]
                                )
                    added_routes_stops.append(file_path.replace(".json", ""))
                except Exception:
                    logging.info(f"Failed to process {file_path}")
                    logging.error(traceback.format_exc())
                    failed_routes_stops.append(file_path.replace(".json", ""))

    logging.info(f"Added {len(stops)} stops ({len(failed_routes_stops)} errors)")
    return stops


def add_routes():
    json_file = '../data/raw/routes.json'
    with open(json_file, 'r') as file:
        routes_json = json.load(file)

    routes = {}
    added_routes = []
    failed_routes = []

    for route in routes_json["data"]:
        try:
            route_id_name = route["routeno"].replace(" UP", "").replace(" DOWN", "")
            if route_id_name not in routes:
                route_long_name = f"{route['fromstation']} ⇔ {route['tostation']}"
                routes[route_id_name] = schedule.AddRoute(
                    short_name=route_id_name, long_name=route_long_name, route_type="Bus"
                )
            added_routes.append(route_id_name)
        except Exception as err:
            logging.info(f"Failed to process {route['routeno']}")
            # logging.info(traceback.format_exc())
            failed_routes.append(route["routeno"])

    logging.info(f"Added {len(added_routes)} routes ({len(failed_routes)} errors)")
    return routes


def add_shapes():
    directory = '../raw/routelines/'
    shapes = {}
    added_shapes = []
    failed_shapes = []

    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            if os.path.getsize(file_path) > 0:  # Check if file is not empty
                try:
                    with open(file_path, 'r') as file:
                        data = json.load(file)
                        if data["data"]:
                            shape_id = filename.replace(".json", "")
                            shapes[shape_id] = transitfeed.Shape(shape_id)
                            for point in data["data"]:
                                shapes[shape_id].AddPoint(lat=point["latitude"], lon=point["longitude"])
                            schedule.AddShapeObject(shapes[shape_id])
                    added_shapes.append(filename.replace("json", ""))
                except Exception as err:
                    logging.info(f"Failed to process {filename}")
                    # logging.info(traceback.format_exc())
                    failed_shapes.append(filename.replace(".json", ""))

    logging.info(f"Added {len(added_shapes)} shapes ({len(failed_shapes)} errors)")
    return shapes


def add_trips(stops_gtfs, routes_gtfs, shapes_gtfs):
    stops_directory = '../raw/stops/'
    timetables_directory = '../raw/timetables/Monday/'

    trips = {}
    added_trips = []
    failed_trips = []
    no_stops = []
    no_timetables = []
    no_shapes = []

    stops_files = set(os.listdir(stops_directory))

    for routename in routes_gtfs:
        for direction in ["UP", "DOWN"]:
            filename = f"{routename} {direction}.json"
            try:
                if filename not in stops_files:
                    no_stops.append(filename)
                    continue

                file_path = os.path.join(stops_directory, filename)
                if os.path.getsize(file_path) == 0:
                    no_stops.append(filename)
                    continue

                shape_key = f"{routename} {direction}"
                if shape_key not in shapes_gtfs:
                    no_shapes.append(filename)
                    continue

                with open(file_path, 'r') as stops_file:
                    stops_data = json.load(stops_file)
                    route = routes_gtfs[routename]
                    timetable_path = os.path.join(timetables_directory, filename)
                    if os.path.getsize(timetable_path) == 0:
                        no_timetables.append(timetable_path)
                        continue

                    with open(timetable_path, 'r') as timetables_file:
                        timetables = json.load(timetables_file)
                        if timetables["Message"] == "No Records Found.":
                            no_timetables.append(timetable_path)
                            continue

                        for trip in timetables["data"][0]["tripdetails"]:
                            direction_id = 0 if direction == "UP" else 1
                            start_time = datetime.datetime.strptime(trip["starttime"], '%H:%M')
                            end_time = datetime.datetime.strptime(trip["endtime"], '%H:%M')
                            duration = (end_time - start_time).total_seconds()

                            trip_obj = route.AddTrip(schedule, headsign=timetables["data"][0]["tostationname"],
                                                     direction_id=direction_id)
                            trip_obj.shape_id = shapes_gtfs[shape_key].shape_id
                            interval = duration / len(stops_data[direction.lower()]["data"])
                            for stop_index, stop in enumerate(stops_data[direction.lower()]["data"]):
                                stop_time = (start_time + datetime.timedelta(seconds=stop_index * interval)).strftime(
                                    '%H:%M:%S')
                                trip_obj.AddStopTime(stops_gtfs[stop["stationid"]], stop_time=stop_time)

                            added_trips.append(filename.replace(".json", ""))
            except Exception as err:
                logging.info(f"Failed to process timetable for route {filename}")
                logging.info(traceback.format_exc())
                failed_trips.append(filename.replace(".json", ""))

    logging.info(f"Added {len(added_trips)} trips ({len(failed_trips)} errors)")
    logging.info(f"Missing timetable for {len(no_timetables)} routes")
    logging.info(f"Missing stops list for {len(no_stops)} routes")
    logging.info(f"Missing shape for {len(no_shapes)} routes")

    for missing_list, filename in [("missingTimetables.txt", no_timetables), ("missingStops.txt", no_stops),
                                   ("missingShapes.txt", no_shapes)]:
        with open(filename, 'w') as file:
            for item in locals()[missing_list]:
                file.write(f"{item}\n")

    return trips


# Main execution
if __name__ == "__main__":
    add_agency()
    add_service_period()
    stops = add_stops()
    routes = add_routes()
    shapes = add_shapes()
    trips = add_trips(stops, routes, shapes)

    # Basic validation
    schedule.Validate()

    # Dump data
    logging.info("Writing GTFS to disk...")
    schedule.WriteGoogleTransitFeed("intermediate/bmtc.zip")
