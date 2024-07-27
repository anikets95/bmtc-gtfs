from scripts import scrape, geojson_creator, gtfs, csv_creator
from python_on_whales import DockerClient

docker = DockerClient(compose_files=["./docker-compose.yml"])


scrape.main()
gtfs.main()
docker.compose.build()
docker.compose.up()
docker.compose.down()
geojson_creator.main()
csv_creator.main()
