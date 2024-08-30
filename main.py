import ee
import geemap
import os
from dotenv import load_dotenv
from datetime import datetime

# Initialize Earth Engine
load_dotenv()
PROJECT_ID = os.getenv("EarthEngine_Project")
ee.Initialize(project=PROJECT_ID)

# Define Hartbeespoort Dam area
hartbeespoort_dam_center = [27.8486, -25.7478]
buffer_distance = 3500  # in meters

def get_rectangle(center, distance):
    lat, lon = center
    delta_deg = distance / 111320  # Convert meters to degrees (approximation)
    return [
        [lat - delta_deg, lon - delta_deg],
        [lat - delta_deg, lon + delta_deg],
        [lat + delta_deg, lon + delta_deg],
        [lat + delta_deg, lon - delta_deg]
    ]

hartbeespoort_dam = ee.Geometry.Polygon(get_rectangle(hartbeespoort_dam_center, buffer_distance))

# Function to get image collection for a specific date range
def get_image_collection(start_date, end_date):
    return (ee.ImageCollection('COPERNICUS/S2')
            .filterBounds(hartbeespoort_dam)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))

# Function to process each image
def process_image(image):
    # Select the RGB bands
    rgb = image.select(['B4', 'B3', 'B2'])

    # Apply the visual parameters
    visParams = {
        'bands': ['B4', 'B3', 'B2'],
        'min': 0,
        'max': 3000,
        'gamma': 1.2
    }

    visualized = rgb.visualize(**visParams)

    # Clip to the area of interest
    return visualized.clip(hartbeespoort_dam)

# Function to download images for a specific time range
def download_images_for_range(start_date, end_date, folder_name):
    collection = get_image_collection(start_date, end_date)
    processed = collection.map(process_image)
    image_list = processed.toList(processed.size())
    date_list = collection.aggregate_array('system:time_start')

    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Download images
    size = image_list.size().getInfo()
    dates = date_list.getInfo()

    for i in range(size):
        image = ee.Image(image_list.get(i))

        # Get the date from the image properties
        if i < len(dates) and dates[i] is not None:
            date = datetime.fromtimestamp(dates[i] / 1000).strftime('%Y-%m-%d')
        else:
            date = f"unknown_date_{i}"

        filename = os.path.join(folder_name, f'hartbeespoort_dam_{date}.tif')

        # Download the image using geemap
        geemap.ee_export_image(
            image,
            filename=filename,
            scale=10,  # 10m resolution, same as Sentinel-2
            region=hartbeespoort_dam,
            file_per_band=False
        )
        print(f'Downloaded: {filename}')

# Define time ranges (example: last 3 years, each year separately)
current_year = datetime.now().year
time_ranges = [
    (f"{current_year - 3}-01-01", f"{current_year - 3}-12-31", f"images_{current_year - 3}"),
    (f"{current_year - 2}-01-01", f"{current_year - 2}-12-31", f"images_{current_year - 2}"),
    (f"{current_year - 1}-01-01", f"{current_year - 1}-12-31", f"images_{current_year - 1}")
]

# Download images for each time range
for start_date, end_date, folder_name in time_ranges:
    print(f"Downloading images for {start_date} to {end_date}")
    download_images_for_range(start_date, end_date, folder_name)

print("All downloads complete!")
