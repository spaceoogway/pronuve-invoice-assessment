import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# =============================================================================
# Dummy Data Function for Park Alarms
# =============================================================================
@st.cache_data(show_spinner=False)
def load_park_alarm_data():
    """Simulate detailed alarm data for the parks."""
    data = [
        {
            "Alarm ID": "ALRM-0001",
            "Park": "Riverside Park",
            "Alarm Type": "Vegetation Health Low",
            "Severity": "High",
            "Description": "NDVI critically low (0.45); urgent vegetation review required.",
            "Timestamp": datetime.now() - timedelta(minutes=15),
        },
        {
            "Alarm ID": "ALRM-0002",
            "Park": "Central Park",
            "Alarm Type": "Water Overuse",
            "Severity": "Medium",
            "Description": "Water consumption exceeded threshold; potential leak or irrigation inefficiency.",
            "Timestamp": datetime.now() - timedelta(minutes=30),
        },
        {
            "Alarm ID": "ALRM-0003",
            "Park": "Lakeside Park",
            "Alarm Type": "Vegetation Health Low",
            "Severity": "Low",
            "Description": "NDVI slightly below optimal levels (0.50); monitor closely.",
            "Timestamp": datetime.now() - timedelta(hours=1),
        },
        {
            "Alarm ID": "ALRM-0004",
            "Park": "Botanical Garden",
            "Alarm Type": "Irrigation Failure",
            "Severity": "High",
            "Description": "Irrigation system malfunction detected; immediate repair needed.",
            "Timestamp": datetime.now() - timedelta(minutes=45),
        },
        {
            "Alarm ID": "ALRM-0005",
            "Park": "City Park",
            "Alarm Type": "Water Overuse",
            "Severity": "Medium",
            "Description": "Consumption spike detected during peak hours; verify meter readings.",
            "Timestamp": datetime.now() - timedelta(hours=2),
        },
        {
            "Alarm ID": "ALRM-0006",
            "Park": "Riverside Park",
            "Alarm Type": "Vegetation Health Low",
            "Severity": "High",
            "Description": "Severe drop in NDVI detected in multiple zones; inspection scheduled.",
            "Timestamp": datetime.now() - timedelta(hours=3),
        },
    ]
    df = pd.DataFrame(data)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df

# =============================================================================
# Park Alarms Page (Maximum Information, No Sliders)
# =============================================================================
def park_alarms():
    st.title("Park Alarms Dashboard")
    st.write(
        """
        This page presents a detailed overview of all active park alarms. Every piece of available information is displayed to help you quickly understand the overall situation. 
        Below you will find summary metrics, charts visualizing alarm distribution and trends, and a detailed table of alarm records.
        """
    )

    # Load data and prepare for display
    df = load_park_alarm_data().copy()
    df.sort_values("Timestamp", ascending=False, inplace=True)
    df["Timestamp_str"] = df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # --- Summary Metrics ---
    st.subheader("Summary Metrics")
    total_alarms = len(df)
    high_count = len(df[df["Severity"] == "High"])
    medium_count = len(df[df["Severity"] == "Medium"])
    low_count = len(df[df["Severity"] == "Low"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Alarms", total_alarms)
    col2.metric("High Severity", high_count)
    col3.metric("Medium Severity", medium_count)
    col4.metric("Low Severity", low_count)

    # --- Alarm Severity Distribution Chart ---
    st.subheader("Alarm Severity Distribution")
    severity_counts = df["Severity"].value_counts().reset_index()
    severity_counts.columns = ["Severity", "Count"]
    fig_severity = px.pie(
        severity_counts,
        values="Count",
        names="Severity",
        title="Distribution of Alarm Severities",
        color="Severity",
        color_discrete_map={"High": "#FF4C4C", "Medium": "#FFA500", "Low": "#90EE90"},
    )
    st.plotly_chart(fig_severity, use_container_width=True)

    # --- Alarm Count by Park Chart ---
    st.subheader("Alarms per Park")
    park_counts = df["Park"].value_counts().reset_index()
    park_counts.columns = ["Park", "Count"]
    fig_park = px.bar(
        park_counts,
        x="Park",
        y="Count",
        color="Park",
        title="Number of Alarms per Park",
        text="Count",
    )
    st.plotly_chart(fig_park, use_container_width=True)

    # --- Alarms Timeline Chart ---
    st.subheader("Alarms Over Time")
    fig_timeline = px.scatter(
        df,
        x="Timestamp",
        y="Park",
        color="Severity",
        size=[15] * len(df),  # Constant marker size for emphasis
        hover_data=["Alarm Type", "Description", "Timestamp_str"],
        title="Timeline of Alarms",
        labels={"Timestamp": "Time", "Park": "Park"},
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

    # --- Detailed Alarm Table ---
    st.subheader("Detailed Alarm Records")
    df_display = df[
        ["Alarm ID", "Park", "Alarm Type", "Severity", "Description", "Timestamp_str"]
    ].rename(columns={"Timestamp_str": "Timestamp"})
    st.dataframe(df_display, use_container_width=True)

    st.markdown(
        """
        **Note:** This dashboard includes every detail currently available for park alarms. 
        For further investigation or action, please refer to the unique Alarm IDs and corresponding descriptions.
        """
    )

# =============================================================================
# Main Function (Standalone Park Alarms Page)
# =============================================================================
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Park Alarms"])
    if page == "Park Alarms":
        park_alarms()

if __name__ == "__main__":
    main()