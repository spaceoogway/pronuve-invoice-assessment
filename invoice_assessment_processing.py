# %% md

# %%
import pandas as pd
from util import similarity, weather

# Import Cankaya Green Area Sheet
df_ca_green_area = pd.read_excel("data/ca_green_area.xlsx", sheet_name=0, header=4)
# Remove "SIRA NO" rows with non-numeric or na values
df_ca_green_area = df_ca_green_area[
    pd.to_numeric(df_ca_green_area["SIRA NO"], errors="coerce").notna()
]
# Convert "SIRA NO" to integer type
df_ca_green_area["SIRA NO"] = df_ca_green_area["SIRA NO"].astype(int)

# %%
# Import all invoices
df_invoice = pd.read_csv("data/all_invoice.csv")
# Get only CANKAYA invoices
df_ca_invoice = df_invoice[df_invoice.district == "ÇANKAYA"].copy()

# Remove "ÇANKAYA BELEDİYESİ" from the "name" column and strip whitespace
df_ca_invoice["name"] = (
    df_ca_invoice["name"].str.replace("ÇANKAYA BELEDİYESİ", "", regex=False).str.strip()
)

# Strip whitespace from column names
df_ca_invoice.columns = df_ca_invoice.columns.str.strip()

# %%
# Convert date columns to datetime.date
df_ca_invoice["start_read_date"] = pd.to_datetime(
    df_ca_invoice["start_read_date"]
).dt.date
df_ca_invoice["end_read_date"] = pd.to_datetime(df_ca_invoice["end_read_date"]).dt.date

# %%
# Get matching names from two dataframes
df_ca_name_similarity = similarity.best_matches(
    list(df_ca_green_area["PARK ADI"].unique()), list(df_ca_invoice["name"].unique())
)

# 1) Filter the similarity DataFrame for high-confidence matches
score_threshold = 0.95
df_ca_name_similarity_filtered = df_ca_name_similarity[
    df_ca_name_similarity.score > score_threshold
].copy()

# 2) Merge df_ca_green_area with the filtered similarity DataFrame (inner join)
df_ca_matched = df_ca_green_area[["PARK ADI", "ÇİM ALAN"]].merge(
    df_ca_name_similarity_filtered[["name_1", "name_2"]],
    how="inner",
    left_on="PARK ADI",
    right_on="name_1",
)

# 3) Rename columns and keep only the columns needed
df_ca_matched.rename(
    columns={"name_2": "name_invoice", "ÇİM ALAN": "grass_area"}, inplace=True
)

# %%
# Create a range of dates for water estimates
date_range = pd.date_range(start="2015-01-01", end="2024-01-10")
dates_without_time = date_range.date
df_date = pd.DataFrame({"date": dates_without_time})

# %%
from functools import partial

# Create a partial function for water estimation
partial_estimate = partial(
    weather.estimate_water_needs, lat=39.9208, lon=32.8541, kc=1, elevation=900
)

df_water_need = partial_estimate(
    start_date=df_date.date.iloc[0], end_date=df_date.date.iloc[-1], park_area=1
)[["date", "water_need_m3"]]


# %%
def calculate_total_water(row, water_data):
    """For a given invoice row, sum water_need_m3 for dates between start and end."""
    start_date = row["start_read_date"]
    end_date = row["end_read_date"]
    mask = (water_data["date"] >= start_date) & (water_data["date"] <= end_date)
    total_water = water_data.loc[mask, "water_need_m3"].sum()
    return total_water


partial_calculate_total_water = partial(calculate_total_water, water_data=df_water_need)

df_ca_invoice["water_need_m3"] = df_ca_invoice.apply(
    partial_calculate_total_water, axis=1
)

# %%
# 4) Merge df_ca_invoice with our matched DataFrame (left join on 'name' vs 'name_invoice')
df_ca_invoice = df_ca_invoice.merge(
    df_ca_matched[["name_invoice", "grass_area"]],
    left_on="name",
    right_on="name_invoice",
    how="left",
)

# 5) Drop rows without grass_area (no match found)
df_ca_invoice.dropna(subset=["grass_area"], inplace=True)

# Calculate total water need for the grass area
df_ca_invoice["water_need_total"] = (
    df_ca_invoice["water_need_m3"] * df_ca_invoice["grass_area"]
)

df_ca_invoice = df_ca_invoice[
    [
        "subscription",
        "name",
        "water_need_total",
        "volume",
        "start_read_date",
        "end_read_date",
        "grass_area",
    ]
].copy()

# Rename "water_need_total" -> "estimated_volume"
df_ca_invoice.rename(columns={"water_need_total": "estimated_volume"}, inplace=True)
df_ca_invoice["estimated_volume"] = df_ca_invoice["estimated_volume"].astype(int)

df_ca_invoice.to_csv("data/ca_invoice.csv", index=False)
