import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# Load and Prepare Data
invoice_df = pd.read_csv("data/ca_invoice.csv")[
    [
        "name",
        "grass_area",
        "start_read_date",
        "end_read_date",
        "volume",
        "estimated_volume",
    ]
]
invoice_df["volume"] = invoice_df["volume"].astype(int)

# Calculate the difference between actual and estimated volume; convert date columns.
invoice_df["difference"] = invoice_df["volume"] - invoice_df["estimated_volume"]
invoice_df["start_read_date"] = pd.to_datetime(invoice_df["start_read_date"]).dt.date
invoice_df["end_read_date"] = pd.to_datetime(invoice_df["end_read_date"]).dt.date

# Streamlit Application Layout
st.title("Actual Water Consumption vs. Weather-Based Water Need Estimation")
st.write(
    """
    This application compares the actual water consumption from invoices for each park with 
    the estimated water need calculated based on weather data (using the Penman–Monteith equation).
    """
)

# Sidebar Filters
st.sidebar.header("Filter Options")

# Filter by park.
parks = invoice_df["name"].unique().tolist()
selected_parks = st.sidebar.multiselect("Select Park(s):", options=parks, default=parks)

# Filter by date range.
min_date = invoice_df["start_read_date"].min()
max_date = invoice_df["end_read_date"].max()
selected_date_range = st.sidebar.date_input("Select Date Range:", [min_date, max_date])

# Apply filters.
filtered_df = invoice_df[invoice_df["name"].isin(selected_parks)]
if len(selected_date_range) == 2:
    start_filter = pd.to_datetime(selected_date_range[0]).date()
    end_filter = pd.to_datetime(selected_date_range[1]).date()
    filtered_df = filtered_df[
        (filtered_df["end_read_date"] >= start_filter)
        & (filtered_df["start_read_date"] <= end_filter)
    ]

# Display Invoice Data and Estimated Water Need
st.subheader("Invoice Data and Estimated Water Need")
# Use .hide_index() to hide the index in the table.
display_df = filtered_df.copy().rename(
    columns={
        "name": "Park Name",
        "grass_area": "Grass Area",
        "start_read_date": "Reading Start Date",
        "end_read_date": "Reading End Date",
        "volume": "Actual Volume (m³)",
        "estimated_volume": "Estimated Volume (m³)",
        "difference": "Difference (m³)",
    }
)
st.dataframe(display_df.style.hide())

# Altair Bar Chart: Actual vs. Estimated Water Volume by Invoice Period
st.subheader("Actual vs. Estimated Water Volume by Invoice Period")

# Create an invoice period column for the chart (e.g., "2023-05-01 - 2023-05-31").
chart_df = filtered_df.copy()
chart_df["Invoice Period"] = (
    chart_df["start_read_date"].astype(str)
    + " - "
    + chart_df["end_read_date"].astype(str)
)

# Melt the data to create a "Type" (actual vs. estimated) for each row.
chart_data = chart_df.melt(
    id_vars=["Invoice Period", "name"],
    value_vars=["volume", "estimated_volume"],
    var_name="Type",
    value_name="Volume (m³)",
)

# Bar chart: If more than one park is selected, facet by park.
if len(selected_parks) > 1:
    bar_chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "Invoice Period:N", title="Invoice Period", axis=alt.Axis(labelLimit=0)
            ),  # Shorten long labels
            xOffset=alt.X("Type:N", title="Volume Type"),
            y=alt.Y("Volume (m³):Q", title="Volume (m³)"),
            color=alt.Color("Type:N", title="Volume Type"),
            tooltip=["name", "Invoice Period", "Type", "Volume (m³)"],
        )
        .properties(width=150, height=200)
        .facet(facet=alt.Facet("name:N", title="Park Name"), columns=2)
    )
else:
    bar_chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "Invoice Period:N", title="Invoice Period", axis=alt.Axis(labelLimit=0)
            ),
            xOffset=alt.X("Type:N", title="Volume Type"),
            y=alt.Y("Volume (m³):Q", title="Volume (m³)"),
            color=alt.Color("Type:N", title="Volume Type"),
            tooltip=["name", "Invoice Period", "Type", "Volume (m³)"],
        )
        .properties(width=600)
    )

st.altair_chart(bar_chart, use_container_width=True)

# Display the Difference (Actual - Estimated)
st.subheader("Difference (Actual - Estimated)")
st.write(
    "A positive value indicates that the actual water consumption is higher than the estimated need, "
    "while a negative value indicates lower consumption."
)

# Create tables sorted by difference.
diff_sorted_asc = filtered_df.sort_values("difference", ascending=True)[
    ["name", "start_read_date", "end_read_date", "difference"]
].rename(
    columns={
        "name": "Park Name",
        "start_read_date": "Reading Start Date",
        "end_read_date": "Reading End Date",
        "difference": "Difference (m³)",
    }
)
diff_sorted_desc = filtered_df.sort_values("difference", ascending=False)[
    ["name", "start_read_date", "end_read_date", "difference"]
].rename(
    columns={
        "name": "Park Name",
        "start_read_date": "Reading Start Date",
        "end_read_date": "Reading End Date",
        "difference": "Difference (m³)",
    }
)

st.markdown("#### Least Watered Invoices (Actual < Estimated)")
st.dataframe(diff_sorted_asc.style.hide())

st.markdown("#### Most Watered Invoices (Actual > Estimated)")
st.dataframe(diff_sorted_desc.style.hide())

# Detailed Daily Water Need Estimation (Placeholder)
st.subheader("Detailed Daily Water Need Estimation")
st.write("Detailed daily estimation will be displayed here...")
