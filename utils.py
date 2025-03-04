import geemap.foliumap as geemap
import pandas as pd
import geopandas as gpd
import ast
from shapely.geometry import Polygon, mapping, box
import folium
import random
import ee
import streamlit as st
import tempfile
from shapely.ops import transform
import pyproj
from functools import partial

def initialize_ee():
    # Access your secrets from .streamlit/secrets.toml
    service_account = st.secrets["ee"]["SERVICE_ACCOUNT"]
    key_file_json = st.secrets["ee"]["KEY_FILE_JSON"]
    google_cloud_project = st.secrets["ee"]["GOOGLE_CLOUD_PROJECT"]
    # Write the fixed JSON key to a temporary file.
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp:
        temp.write(key_file_json)
        temp.flush()
        key_file_path = temp.name

    credentials = ee.ServiceAccountCredentials(service_account, key_file_path)
    ee.Initialize(credentials, project=google_cloud_project)

def create_aoi(center, buffer):
    return ee.Geometry.Rectangle([
        center[1] - buffer, center[0] - buffer,
        center[1] + buffer, center[0] + buffer
    ])

def get_park_bounds(gdf, park_name):
    """Get the bounds of a specific park with a small margin"""
    if park_name == "Seçiniz..." or park_name is None:
        return None

    # Filter to the selected park
    park_geom = gdf[gdf["name"] == park_name].iloc[0]["geometry"]

    # Get the bounds with a small margin (5%)
    minx, miny, maxx, maxy = park_geom.bounds

    # Calculate margin based on park size
    width = maxx - minx
    height = maxy - miny
    margin = max(width, height) * 0.1  # 10% margin

    # Create a slightly larger bounding box
    bounds = (
        miny - margin,  # south
        minx - margin,  # west
        maxy + margin,  # north
        maxx + margin   # east
    )

    return bounds

def get_satellite_image(aoi, start_date, end_date):
    collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterBounds(aoi)
                  .filterDate(start_date, end_date)
                  .sort('CLOUDY_PIXEL_PERCENTAGE'))
    image = collection.first()  # Choose the least cloudy image
    return image

def compute_ndvi(image):
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return ndvi

def load_csv_polygons(csv_file):
    df = pd.read_csv(csv_file)
    df['geometry'] = df['polygon'].apply(lambda x: Polygon(ast.literal_eval(x)))
    colors = ["green", "blue", "red"]
    df['color'] = df.apply(lambda row: random.choice(colors), axis=1)
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
    return gdf

def add_park_polygons(m, csv_file, selected_park=None):
    gdf = load_csv_polygons(csv_file)

    # Prepare the styling for the parks
    if selected_park and selected_park != "Seçiniz...":
        # Only show the selected park with highlighted style
        filtered_gdf = gdf[gdf["name"] == selected_park]

        # If park is found, fit the map bounds to this park
        if not filtered_gdf.empty:
            park_geom = filtered_gdf.iloc[0]["geometry"]
            minx, miny, maxx, maxy = park_geom.bounds
            # Add a small margin
            margin = max(maxx - minx, maxy - miny) * 0.1
            m.fit_bounds([
                [miny - margin, minx - margin],
                [maxy + margin, maxx + margin]
            ])
    else:
        # Show all parks
        filtered_gdf = gdf

    # Style function for GeoJSON
    def style_function(feature):
        park_name = feature["properties"].get("name", "")

        if selected_park and park_name == selected_park:
            # Highlighted style for selected park
            return {
                'color': 'red',
                'weight': 3,
                'fillOpacity': 0
            }
        else:
            # Regular style for other parks
            return {
                'color': feature['properties'].get('color', 'blue'),
                'weight': 2,
                'fillOpacity': 0
            }

    # Add the GeoJSON layer
    geojson_data = filtered_gdf.to_json()
    geojson_layer = folium.GeoJson(
        geojson_data,
        name="Park Polygons",
        style_function=style_function,
        tooltip=folium.features.GeoJsonTooltip(fields=['name'], aliases=["Park: "])
    )
    geojson_layer.add_to(m)

    # Create the union for NDVI mask
    union_geom = filtered_gdf.union_all()
    ee_union = ee.Geometry(mapping(union_geom))
    return ee_union

def create_map(aoi_center, ndvi_masked):
    # Create the map; center is [lat, lon], zoom=10
    m = geemap.Map(center=aoi_center, zoom=12)
    # Remove default layers
    m.layers = []
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        max_zoom=25,
        name='Google Satellite'
    ).add_to(m)

    ndvi_vis = {
        "min": 0.0,
        "max": 0.8,
        "palette": [
            "FFFFFF", "CE7E45", "DF923D", "F1B555", "FCD163",
            "99B718", "74A901", "66A000", "529400", "3E8601",
            "207401", "056201", "004C00"
        ]
    }
    m.addLayer(ndvi_masked, ndvi_vis, "NDVI (Inside Parks)")
    return m

def create_map_with_layers(aoi_center, ndvi_masked, zoom_level=12):
    # Create the map with selected layers
    m = geemap.Map(center=aoi_center, zoom=zoom_level)
    # Remove default layers
    m.layers = []


    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        max_zoom=25,
        name='Uydu Görüntüsü'
    ).add_to(m)

    return m

def add_ndvi_layer(m, parks_union, ndvi):
    mask = ee.Image.constant(1).clip(parks_union)
    ndvi_masked = ndvi.updateMask(mask)
    # Replace any old NDVI layer with the masked one
    m.layers = [
        layer for layer in m.layers
        if getattr(layer, 'layer_name', None) != "NDVI (Inside Parks)"
    ]
    m.addLayer(
        ndvi_masked,
        {
            "min": 0.0,
            "max": 0.8,
            "palette": [
                "FFFFFF", "CE7E45", "DF923D", "F1B555", "FCD163",
                "99B718", "74A901", "66A000", "529400", "3E8601",
                "207401", "056201", "004C00"
            ]
        },
        "NDVI (Inside Parks)", shown=False
    )
    return m

def add_drawing_tools(m):
    """
    Add drawing tools to the map without complex callbacks
    """
    # Add a basic drawing toolbar
    folium.plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': False,
            'rectangle': True,
            'circle': False,
            'marker': False,
            'circlemarker': False,
            'polygon': True
        }
    ).add_to(m)

    return m

def calculate_area(lat1, lon1, lat2, lon2, lat3, lon3):
    """
    Calculate the area of a triangle in square meters using coordinates
    """
    # Create a triangle from the coordinates
    triangle = Polygon([(lon1, lat1), (lon2, lat2), (lon3, lat3)])

    # Define the projection transformations for Turkey
    wgs84 = pyproj.CRS('EPSG:4326')  # WGS84 latitude/longitude
    utm = pyproj.CRS('EPSG:32636')   # UTM zone 36N (for Turkey)

    # Create the transformer
    project = partial(
        pyproj.transform,
        pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    )

    # Transform the polygon to UTM
    utm_polygon = transform(project, triangle)

    # Calculate the area in square meters
    return utm_polygon.area

def add_custom_areas_to_map(m, custom_areas):
    """Add the saved custom areas to the map."""
    # Define colors for different area types
    area_colors = {
        "Çim": "green",
        "Ağaç": "darkgreen",
        "Çalı": "lightgreen",
        "Havuz": "blue",
        "Çocuk Oyun Alanı": "orange",
        "Halı Saha": "#8B4513"  # Brown
    }

    # Add areas to map
    for i, area in enumerate(custom_areas):
        color = area_colors.get(area["type"], "gray")

        # For simplicity, we'll just use rectangular areas
        folium.Rectangle(
            bounds=[(area["lat1"], area["lon1"]), (area["lat2"], area["lon2"])],
            color="black",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"{area['name']} - {area['area_m2']:.1f} m²"
        ).add_to(m)

    return m