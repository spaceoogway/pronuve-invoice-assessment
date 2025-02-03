# Actual Water Consumption vs. Weather-Based Water Need Estimation

This application compares the actual water consumption from invoices for each park with the estimated water need calculated based on weather data using the Penman–Monteith equation.

## Project Structure

```plaintext
app.py
data/
    all_invoice.csv
    ca_green_area.xlsx
ca_invoice.csv
ca_park_personnel.csv
invoice_assessment_processing.py
penman–monteith.md
README.md
util/
    similarity.py
    weather.py
```

## Installation

1. Clone the repository:

   ```sh
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a virtual environment and activate it:

   ```sh
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:

   ```sh
   pip install -r requirements.txt
   ```

## Usage

1. Ensure that the data files are in the data directory.

2. Run the Streamlit application:

   ```sh
       streamlit run app.py
   ```

## Files

- `app.py`: Main application file that sets up the Streamlit interface and visualizations.
- `ca_invoice.csv`: Contains invoice data for various parks.
- `ca_park_personnel.csv`: Contains personnel data for parks.
- invoice_assessment_processing.py: Script for processing invoice assessments.
- `penman–monteith.md`: Documentation on the Penman–Monteith equation used for water need estimation.
- `similarity.py`: Utility functions for similarity calculations.
- `weather.py`: Utility functions for weather data processing.

## Features

- **Filter Options**: Filter data by park and date range.
- **Data Display**: View invoice data and estimated water need.
- **Visualizations**: Compare actual vs. estimated water volume using bar charts.
- **Difference Analysis**: View tables sorted by the difference between actual and estimated water consumption.

## Data Sources

- `ca_invoice.csv`: Contains columns such as `name`, `grass_area`, `start_read_date`, `end_read_date`, `volume`, and `estimated_volume`.
- `ca_park_personnel.csv`: Contains personnel information for different parks.

## Calculation Details

The estimated water need is calculated using the Penman–Monteith equation, as documented in `penman–monteith.md`.
