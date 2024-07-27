# bmtc-gtfs

Unofficial GTFS dataset for BMTC routes, stops and timetables in Bengaluru. Raw data sourced from Namma BMTC app, parsed and saved as GTFS. This is a fork of Vonter's [repo](https://github.com/Vonter/bmtc-gtfs)

## Motivation

- [Why BMTC?](https://datameet.org/2016/08/05/bmtc-intelligent-transportation-system-its-open-transport-data/)
- [Why GTFS?](https://gtfs.org/#why-use-gtfs)

## Caveat

The source for the data and analysis in this repository are the routes, stops and timetables as displayed on the Namma BMTC app. However, the Namma BMTC app is not completely accurate, and is particularly unreliable for timetables and stop timings. Nonetheless, the data can be used to understand general trends in the BMTC network.

Due to the design of the Namma BMTC app, only routes with functional live tracking are included in the GTFS. Any missing routes may be due to live tracking unavailability and not necessarily due to the route being inoperational.

## GTFS

The GTFS dataset can be found **[here](bmtc-data/gtfs/bmtc.zip?raw=1)**

## Maps

### Route frequency

### Stop frequency

### Most frequent route

### Most frequent stop

## GeoJSON

GeoJSONs can be found below:
- [Routes](bmtc-data/geojson/routes.geojson?raw=1)
- [Stops](bmtc-data/geojson/stops.geojson?raw=1)
- [Aggregated Stops](bmtc-data/geojson/aggregated.geojson?raw=1)

Conversion into other formats can be done using free tools like [mapshaper](https://mapshaper.org/) or [QGIS](https://qgis.org/en/site/)

## CSV

CSVs can be found below:
- [Routes](bmtc-data/csv/routes.csv?raw=1)
- [Stops](bmtc-data/csv/stops.csv?raw=1) 
- [Aggregated Stops](bmtc-data/csv/aggregated.csv?raw=1) 

## HTML

Visualize the routes, stops and timetables in the GTFS dataset, with a web browser: #TBD

## Validations

- [gtfs-validator](bmtc-data/validation/gtfs-validator)
- [gtfsvtor](bmtc-data/validation/gtfsvtor)
- [transport-validator](bmtc-data/validation/transport-validator)

## Scripts

- [scrape.py](scripts/scrape.py): Scrape raw data from Namma BMTC
- [gtfs.py](scripts/gtfs.py): Parse raw data and save as GTFS
- [geojson_creator.py](scripts/geojson_creator.py): Process the GTFS and output a GeoJSON representing the network
- [csv_creator.py](scripts/csv_creator.py): Process the GeoJSON and output a CSV
- [orchestrator.py](scripts/orchestrator_creator.py): Orchestrate Complete Process
- [docker-compose.yml](docker-compose.yml): Handles Linting, Validation and HTML conversion of GTFS data


## Raw JSON

Raw JSON data scraped from Namma BMTC can be found below:

- [routelines.zip](bmtc-data/raw/routelines.zip?raw=1): Pointwise co-ordinates of each route
- [stops.zip](bmtc-data/raw/stops.zip?raw=1): Stops through which each route passes
- [timetables.zip](bmtc-data/raw/timetables.zip?raw=1): Timetables for each route

## To-do

- Refactor/optimize scripts
    - Fix validation errors and warnings
    - https://gtfstohtml.com/docs/configuration
    - Fix missing/failed routes/stops/timetables
    - Minimize network calls
    - Speed up data processing
    - GitHub Actions workflow
    - Daily update of route/stop/timetable changes
- Add maps (and data analysis)
    - [Route series-wise maps](https://github.com/geohacker/bmtc#2-and-3-series-routes)
    - [Directionality](https://github.com/geohacker/bmtc#direction)
    - [Reachability](https://github.com/geohacker/bmtc#reachability)
    - [Redundancy](https://github.com/geohacker/bmtc#redundancy)
    - [Access to amenities](https://github.com/geohacker/bmtc#school-walkability) (education, health, recreation, employment)
- Add fare information

## Contributing

Interested in contributing or want to know more? Join the [bengwalk Discord Server](https://discord.com/invite/Sdkhu5MYnA)

## Credits

- [Namma BMTC](https://bmtcwebportal.amnex.com/commuter/dashboard)
- [transitfeed](https://github.com/google/transitfeed)
- [gtfstidy](https://github.com/patrickbr/gtfstidy)
- [gtfs-validator](https://github.com/MobilityData/gtfs-validator)
- [gtfsvtor](https://github.com/mecatran/gtfsvtor)
- [transport-validator](https://github.com/etalab/transport-validator)
- [gtfs_kit](https://github.com/mrcagney/gtfs_kit)

## Inspiration

- [geohacker](https://github.com/geohacker/bmtc)
- [planemad](https://bitterscotch.wordpress.com/tag/chennai-bus-map/)
- [nikhilvj](http://nikhilvj.co.in/files/bmtc-gtfs/)
- [openbangalore](https://dataspace.mobi/dataset/bengaluru-public-transport-gtfs-static)
- [mauryam](https://github.com/mauryam/gtfs-data)
- [vonter](https://github.com/Vonter/bmtc-gtfs)
