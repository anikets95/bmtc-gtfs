import os

import geopandas as gpd


def main():
    with os.scandir("bmtc-data/geojson") as raw_directory:
        for raw_item in raw_directory:
            if raw_item.name.endswith(".geojson"):
                # Path to your GeoJSON file
                geojson_path = 'bmtc-data/geojson/' + raw_item.name
                # Desired output CSV file path
                csv_path = 'bmtc-data/csv/' + raw_item.name.split(".geojson")[0] + ".csv"

                # Read the GeoJSON file
                gdf = gpd.read_file(geojson_path)

                # Optionally, convert the geometry to a string if you want to include it in the CSV
                # This will convert the geometry to Well-Known Text (WKT) format
                gdf['geometry'] = gdf['geometry'].apply(lambda x: x.wkt)

                # Save the DataFrame to CSV
                gdf.to_csv(csv_path, index=False)


if __name__ == '__main__':
    main()
