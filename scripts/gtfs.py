import datetime
import json
import logging
import os
import shutil
import traceback
import zipfile

import transitfeed

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/gtfs-debug.log"),
        logging.StreamHandler()
    ]
)

schedule = transitfeed.Schedule()


def add_agency():
    schedule.AddAgency("Bengaluru Metropolitan Transport Corporation",
                       "https://mybmtc.karnataka.gov.in/english", "Asia/Kolkata", agency_id=1)


def add_service_period():
    service_period = schedule.GetDefaultServicePeriod()
    start_date = datetime.datetime.now() + datetime.timedelta(days=1)
    end_date = datetime.datetime.now() + datetime.timedelta(days=7)
    service_period.SetStartDate(start_date.strftime("%Y%m%d"))
    service_period.SetEndDate(end_date.strftime("%Y%m%d"))
    service_period.SetWeekdayService(True)
    service_period.SetDayOfWeekHasService(5, True)  # Saturday
    service_period.SetDayOfWeekHasService(6, True)  # Sunday


def process_json_files(directory, process_function):
    results = {"success": [], "failure": []}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            # Check if file is not empty
            if os.path.getsize(file_path) > 0:
                try:
                    with open(file_path, 'r') as file:
                        data = json.load(file)
                        process_function(file_path, data, results)
                except Exception:
                    logging.info(f"Failed to process {file_path}")
                    logging.error(traceback.format_exc())
                    results["failure"].append(file_path.replace(".json", ""))
    return results


def add_stops():
    stops = {}
    directory = 'bmtc-data/raw/stops/'

    def process_stop_file(file_path, data, results):
        for stop in (data.get("up", {}).get("data", []) + data.get("down", {}).get("data", [])):
            if stop["stationid"] not in stops:
                stops[stop["stationid"]] = schedule.AddStop(
                    lng=stop["centerlong"],
                    lat=stop["centerlat"],
                    name=stop["stationname"],
                    stop_id=str(stop["stationid"])
                )
        results["success"].append(file_path.replace(".json", ""))

    results = process_json_files(directory, process_stop_file)
    logging.info(f"Added {len(stops)} stops ({len(results['failure'])} errors)")
    return stops


def add_routes():
    routes = {}
    json_file = 'bmtc-data/raw/routes.json'

    with open(json_file, 'r') as file:
        routes_json = json.load(file)

    for route in routes_json["data"]:
        try:
            route_id_name = route["routeno"].replace(" UP", "").replace(" DOWN", "")
            if route_id_name not in routes:
                route_long_name = f"{route['fromstation']} ⇔ {route['tostation']}"
                routes[route_id_name] = schedule.AddRoute(
                    short_name=route_id_name,
                    long_name=route_long_name,
                    route_type="Bus",
                    route_id=route["routeid"]
                )
            # routes[route_id_name] = route_id_name
        except Exception as err:
            logging.info(f"Failed to process {route['routeno']}")
            logging.error(traceback.format_exc())

    logging.info(f"Added {len(routes)} routes")
    return routes


def add_shapes():
    shapes = {}
    directory = 'bmtc-data/raw/routelines/'

    def process_shape_file(file_path, data, results):
        if data.get("data"):
            shape_id = os.path.basename(file_path).replace(".json", "")
            shapes[shape_id] = transitfeed.Shape(shape_id)
            for point in data["data"]:
                shapes[shape_id].AddPoint(lat=point["latitude"], lon=point["longitude"])
            schedule.AddShapeObject(shapes[shape_id])
            results["success"].append(file_path.replace(".json", ""))

    results = process_json_files(directory, process_shape_file)
    logging.info(f"Added {len(shapes)} shapes ({len(results['failure'])} errors)")
    return shapes


def add_trips(stops_gtfs, routes_gtfs, shapes_gtfs):
    stops_directory = 'bmtc-data/raw/stops/'
    # TODO: Iterate through next day maybe rather than Monday always ?
    timetables_directory = 'bmtc-data/raw/timetables/Monday/'

    trips = []
    no_stops = []
    no_timetables = []
    no_shapes = []

    stops_files = set(os.listdir(stops_directory))

    def process_trip(route, direction, filename):
        file_path = os.path.join(stops_directory, filename)
        shape_key = f"{route} {direction}"
        timetable_path = os.path.join(timetables_directory, filename)

        if filename not in stops_files or os.path.getsize(file_path) == 0:
            no_stops.append(filename)
            return

        if shape_key not in shapes_gtfs:
            no_shapes.append(filename)
            return

        with open(file_path, 'r') as stops_file:
            stops_data = json.load(stops_file)

            if not os.path.exists(timetable_path) or os.path.getsize(timetable_path) == 0:
                no_timetables.append(timetable_path)
                return

            with open(timetable_path, 'r') as timetables_file:
                timetables = json.load(timetables_file)

                if timetables["Message"] == "No Records Found.":
                    no_timetables.append(timetable_path)
                    return

                for trip in timetables["data"][0]["tripdetails"]:
                    direction_id = 0 if direction == "UP" else 1

                    # TODO: Better duration calculation
                    start_time = datetime.datetime.strptime(trip["starttime"], '%H:%M')
                    end_time = datetime.datetime.strptime(trip["endtime"], '%H:%M')
                    duration = (end_time - start_time).total_seconds()

                    trip_obj = routes_gtfs[route].AddTrip(schedule, headsign=timetables["data"][0]["tostationname"])
                    trip_obj.shape_id = shapes_gtfs[shape_key].shape_id
                    trip_obj.direction_id = direction_id
                    interval = duration / len(stops_data[direction.lower()]["data"])

                    for stop_index, stop in enumerate(stops_data[direction.lower()]["data"]):
                        stop_time = (start_time + datetime.timedelta(seconds=stop_index * interval)).strftime(
                            '%H:%M:%S')
                        trip_obj.AddStopTime(stops_gtfs[stop["stationid"]], stop_time=stop_time)

                trips.append(filename.replace(".json", ""))

    for routename in routes_gtfs:
        for direction in ["UP", "DOWN"]:
            filename = f"{routename} {direction}.json"
            try:
                process_trip(routename, direction, filename)
            except Exception as err:
                logging.info(f"Failed to process timetable for route {filename}")
                logging.error(traceback.format_exc())

    logging.info(f"Added {len(trips)} trips")
    logging.info(f"Missing timetable for {len(no_timetables)} routes")
    logging.info(f"Missing stops list for {len(no_stops)} routes")
    logging.info(f"Missing shape for {len(no_shapes)} routes")

    with open('bmtc-data/gtfs/intermediate/missingTimetables.txt', 'w') as file:
        for item in no_timetables:
            file.write("%s\n" % item)
    with open('bmtc-data/gtfs/intermediate/missingStops.txt', 'w') as file:
        for item in no_stops:
            file.write("%s\n" % item)
    with open('bmtc-data/gtfs/intermediate/missingShapes.txt', 'w') as file:
        for item in no_shapes:
            file.write("%s\n" % item)



def compress_files():
    with os.scandir("bmtc-data/raw") as raw_directory:
        for raw_item in raw_directory:
            if raw_item.is_dir():
                folder_path = raw_item.name
                folder_name = os.path.basename(folder_path.rstrip('/\\'))
                zip_file_path = os.path.join("bmtc-data/raw", os.path.dirname(folder_path), f"{folder_name}.zip")

                with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(os.path.join("bmtc-data/raw", folder_path)):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, start=folder_path)
                            zipf.write(file_path, arcname)

                logging.info(f"Folder '{folder_path}' compressed into '{zip_file_path}'")

                shutil.rmtree(os.path.join("bmtc-data/raw", folder_path))

            else:
                file_name = raw_item.name
                if file_name.endswith(".json"):
                    os.remove(os.path.join("bmtc-data/raw", file_name))


def main():
    add_agency()
    add_service_period()
    stops = add_stops()
    routes = add_routes()
    shapes = add_shapes()
    add_trips(stops, routes, shapes)

    # Basic validation
    schedule.Validate()

    # Dump data
    logging.info("Writing GTFS to disk...")

    schedule.WriteGoogleTransitFeed("bmtc-data/gtfs/intermediate/bmtc.zip")

    compress_files()


# Main execution
if __name__ == "__main__":
    main()
