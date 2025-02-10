import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime
import calendar
from dateutil import rrule

# --- Page configuration: wide layout and custom title ---
st.set_page_config(page_title="Water Consumption Dashboard", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
/* Hide default Streamlit elements */
header, footer, .css-18ni7ap {visibility: hidden;}

/* Global font and background */
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    background-color: #f4f4f4;
    overflow: hidden;  /* Prevent scrolling */
}

/* KPI card style: equal size, centered content */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    margin: 0.5rem;
    min-width: 200px;
    min-height: 150px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.kpi-card h3 {
    margin: 0.2rem 0;
    color: #333;
    font-size: 1.2rem;
}
.kpi-card p {
    font-size: 1.8rem;
    font-weight: bold;
    margin: 0.2rem 0;
    color: #0077c0;
}
.kpi-card small {
    color: #666;
}

/* Filter container style: a horizontal bar at the top */
.filter-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.5rem;
    margin-bottom: 1rem;
}
.filter-container > div {
    flex: 1;
    margin-right: 1rem;
}
.filter-container > div:last-child {
    margin-right: 0;
}

/* Increase width for select boxes so that full park names display */
div[data-baseweb="select"] {
    min-width: 250px;
    white-space: nowrap;
}

/* Tabs: add a little extra gap between tab labels */
.stTabs [role=tablist] {
    gap: 1rem;
}
</style>
""", unsafe_allow_html=True)

# --- Load and Prepare Data ---
invoice_df = pd.read_csv("data/ca_invoice.csv", usecols=["name", "grass_area", "start_read_date", "end_read_date", "volume", "estimated_volume"])
invoice_df["volume"] = invoice_df["volume"].astype(int)
invoice_df["difference"] = invoice_df["volume"] - invoice_df["estimated_volume"]
invoice_df["start_read_date"] = pd.to_datetime(invoice_df["start_read_date"]).dt.date
invoice_df["end_read_date"]   = pd.to_datetime(invoice_df["end_read_date"]).dt.date

# Compute the min and max months in the dataset (for building month-year selectors)
min_date = invoice_df["start_read_date"].min()
max_date = invoice_df["end_read_date"].max()

# Generate a list of the 1st day of each month from min_date to max_date
def month_range(start_date, end_date):
    """Return a list of date objects (YYYY-mm-01) from start_date to end_date (inclusive) monthly."""
    start = date(start_date.year, start_date.month, 1)
    end   = date(end_date.year, end_date.month, 1)
    months = []
    for dt in rrule.rrule(rrule.MONTHLY, dtstart=start, until=end):
        months.append(dt.date())
    return months

all_months = month_range(min_date, max_date)

def format_month(dt: date) -> str:
    """Format a date object in 'YYYY-MM' form for display."""
    return dt.strftime("%Y-%m")

# --- Filter Controls at the Top ---
with st.container():
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        # Park selection in Turkish
        parks = invoice_df["name"].unique().tolist()
        if "ÇANKAYA" not in parks:
            parks.insert(0, "ÇANKAYA")
        default_index = parks.index("ÇANKAYA")
        selected_park = st.selectbox("Park Seçiniz:", parks, index=default_index)

    with col2:
        # Start month-year
        st.write("Başlangıç Ay/Yıl")
        start_mo = st.selectbox(
            "",  # label is above
            options=[format_month(m) for m in all_months],
            index=0  # pick the earliest by default
        )

    with col3:
        # End month-year
        st.write("Bitiş Ay/Yıl")
        end_mo = st.selectbox(
            "",  # label is above
            options=[format_month(m) for m in all_months],
            index=len(all_months) - 1  # pick the latest by default
        )

    st.markdown("</div>", unsafe_allow_html=True)

# Convert the chosen month-year strings back into date objects
start_year, start_month = map(int, start_mo.split("-"))
end_year, end_month     = map(int, end_mo.split("-"))

start_filter = date(start_year, start_month, 1)
# For the end filter, we get the last day of that month
end_day = calendar.monthrange(end_year, end_month)[1]
end_filter = date(end_year, end_month, end_day)

# Ensure the user hasn't swapped start/end
if start_filter > end_filter:
    st.warning("Başlangıç ayı, bitiş ayından sonra seçildi. Değerler ters çevriliyor.")
    start_filter, end_filter = end_filter, start_filter

# --- Apply Filters ---
if selected_park == "ÇANKAYA":
    park_filtered_df = invoice_df.copy()
else:
    park_filtered_df = invoice_df[invoice_df["name"] == selected_park]

date_filtered_df = park_filtered_df[
    (park_filtered_df["end_read_date"]   >= start_filter) &
    (park_filtered_df["start_read_date"] <= end_filter)
    ]

filtered_df = date_filtered_df.copy()

# --- Prepare Display DataFrame with Turkish column names ---
filtered_df["difference_pct"] = (
        (filtered_df["difference"] / filtered_df["estimated_volume"]) * 100
).replace([float("inf"), float("-inf")], 0)  # Handle zero or negative est_volume

filtered_df["difference_pct"] = filtered_df["difference_pct"].fillna(0)

display_df = (
    filtered_df
    .drop(columns=["grass_area"])
    .rename(columns={
        "name":             "Park Adı",
        "start_read_date":  "Başlangıç Tarihi",
        "end_read_date":    "Bitiş Tarihi",
        "volume":           "Gerçek (m³)",
        "estimated_volume": "Tahmin (m³)",
        "difference":       "Fark (m³)",
        "difference_pct":   "Fark (%)"
    })
)

# Sort the invoice table by latest Bitiş Tarihi descending
display_df = display_df.sort_values("Bitiş Tarihi", ascending=False)

# --- Calculate KPIs ---
total_actual    = filtered_df["volume"].sum()
total_estimated = filtered_df["estimated_volume"].sum()
total_diff      = filtered_df["difference"].sum()
invoice_count   = len(filtered_df)
variance_percent = (total_diff / total_estimated * 100) if total_estimated != 0 else 0

# --- Create Two Tabs: "Genel Bakış" and "Faturalar" ---
tabs = st.tabs(["Genel Bakış", "Faturalar"])

# ========= GENEL BAKIŞ Tab =========
with tabs[0]:
    # 1) KPI Cards (in English, as requested to keep rest in English)
    with st.container():
        kpi_cards = [
            {
                "title": "Total Actual",
                "value": f"{total_actual:,} m³",
                "subtitle": "Actual water consumption"
            },
            {
                "title": "Total Estimated",
                "value": f"{total_estimated:,} m³",
                "subtitle": "Forecasted water need"
            },
            {
                "title": "Total Difference",
                "value": f"{total_diff:,} m³",
                "subtitle": f"{variance_percent:.1f}% variance"
            },
            {
                "title": "Invoices",
                "value": f"{invoice_count}",
                "subtitle": "Records analyzed"
            }
        ]
        kpi_cols = st.columns(len(kpi_cards))
        for col, kpi in zip(kpi_cols, kpi_cards):
            col.markdown(f"""
                <div class="kpi-card">
                    <h3>{kpi['title']}</h3>
                    <p>{kpi['value']}</p>
                    <small>{kpi['subtitle']}</small>
                </div>
            """, unsafe_allow_html=True)

    # 2) Altair Chart: Horizontal Bar, show all bars/labels
    with st.container():
        chart_df = filtered_df.copy()
        # Create a column "Invoice Period" as "start - end"
        chart_df["Invoice Period"] = (
                chart_df["start_read_date"].astype(str)
                + " - "
                + chart_df["end_read_date"].astype(str)
        )
        # Convert for sorting
        chart_df["start_read_datetime"] = pd.to_datetime(chart_df["start_read_date"])

        # Melt for "Gerçek" vs. "Tahmin"
        chart_data = chart_df.melt(
            id_vars=["Invoice Period", "start_read_datetime", "name"],
            value_vars=["volume", "estimated_volume"],
            var_name="Type",
            value_name="Volume (m³)"
        )

        # Sort invoice periods in descending order based on start_read_datetime
        sorted_periods = (
            chart_df
            .sort_values("start_read_datetime", ascending=False)["Invoice Period"]
            .unique()
            .tolist()
        )

        bar_chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                y=alt.Y(
                    "Invoice Period:N",
                    sort=sorted_periods,
                    axis=alt.Axis(
                        title="Fatura Dönemi",
                        labelLimit=1000,
                        labelOverlap=False,
                        values=sorted_periods  # Force all labels
                    )
                ),
                x=alt.X("Volume (m³):Q", title="Tüketim (m³)"),
                color=alt.Color("Type:N", title="Volume Type"),
                tooltip=[
                    alt.Tooltip("name", title="Park Name"),
                    alt.Tooltip("start_read_datetime:T", title="Start Date"),
                    alt.Tooltip("Invoice Period:N", title="Period"),
                    alt.Tooltip("Type:N", title="Type"),
                    alt.Tooltip("Volume (m³):Q", title="Volume")
                ]
            )
            .properties(width="container", height=500)
        )

        st.altair_chart(bar_chart, use_container_width=True)

# ========= FATURALAR Tab =========
with tabs[1]:
    with st.container():
        st.markdown("<h2 style='text-align: center;'>Faturalar</h2>", unsafe_allow_html=True)
        # We only color the "Fark (%)" column
        styled_df = display_df.style.background_gradient(
            subset=["Fark (%)"],  # Only color percentage difference
            cmap='coolwarm'
        )
        st.dataframe(styled_df, height=500)