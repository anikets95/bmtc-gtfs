import json
import os
from datetime import datetime
from dotenv import load_dotenv

from python_on_whales import DockerClient

from scripts import geojson_creator, csv_creator, scrape, gtfs

docker = DockerClient(compose_files=["./docker-compose.yml"])


# Load environment variables from the .env file
load_dotenv()


# Function to read, edit, and save JSON
def modify_json(file_path, key, new_value):
    # Step 1: Read the JSON file
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Step 2: Modify the JSON data
    data[key] = new_value

    # Step 3: Write the updated JSON back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


config_path = "bmtc-data/html/config.json"
scrape.main()
gtfs.main()
modify_json(config_path, "effectiveDate", datetime.now().strftime("%B %d, %Y"))
modify_json(config_path, "mapboxAccessToken", os.getenv("MAPBOX_ACCESS_TOKEN"))
docker.compose.build()
docker.compose.up()
docker.compose.down()
geojson_creator.main()
csv_creator.main()
modify_json(config_path, "mapboxAccessToken", "")
