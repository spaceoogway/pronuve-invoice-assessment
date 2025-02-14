import calendar
import streamlit as st
import pandas as pd
import altair as alt

from datetime import date, timedelta
from dateutil import rrule

# Make sure this is the very first Streamlit call for wide layout!
st.set_page_config(page_title="Su Tüketimi Panosu", layout="wide")

# Import and inject custom CSS styling.
from style import inject_css, inject_logo

inject_css()

# -- Data Loading and Preprocessing --
invoice_df = pd.read_csv(
    "data/final/ca_invoice.csv",
    usecols=[
        "name",
        "grass_area",
        "start_read_date",
        "end_read_date",
        "volume",
        "estimated_volume",
    ],
)
invoice_df["volume"] = invoice_df["volume"].astype(int)
invoice_df["difference"] = invoice_df["volume"] - invoice_df["estimated_volume"]

invoice_df["start_read_date"] = pd.to_datetime(invoice_df["start_read_date"]).dt.date
invoice_df["end_read_date"] = pd.to_datetime(invoice_df["end_read_date"]).dt.date
invoice_df = invoice_df[
    invoice_df["start_read_date"] >= pd.to_datetime("2015-01-01").date()
]

min_date = invoice_df["start_read_date"].min()
max_date = invoice_df["start_read_date"].max()


def month_range(start_date, end_date):
    start = date(start_date.year, start_date.month, 1)
    end = date(end_date.year, end_date.month, 1)
    months = []
    for dt in rrule.rrule(rrule.MONTHLY, dtstart=start, until=end):
        months.append(dt.date())
    return months


def format_month(dt: date) -> str:
    return dt.strftime("%Y-%m")


all_months = sorted(month_range(min_date, max_date), reverse=True)


def get_month_index(yyyy_mm: str) -> int:
    for i, m in enumerate(all_months):
        if format_month(m) == yyyy_mm:
            return i
    return 0


# -- Top Row: Logo and Selection Controls --
# Create four columns: one narrow for the logo and three for the select boxes.
col_logo, col1, col2, col3 = st.columns([1, 3, 3, 3])

with col_logo:
    inject_logo()

with col1:
    unique_parks = invoice_df["name"].unique().tolist()
    # "ÇANKAYA" is treated as the “all parks” option
    if "ÇANKAYA" not in unique_parks:
        unique_parks.insert(0, "ÇANKAYA")
    park_index = unique_parks.index("ÇANKAYA")
    selected_park = st.selectbox("Park Seçiniz:", unique_parks, index=park_index)

with col2:
    start_default = get_month_index("2016-01")
    start_mo = st.selectbox(
        "Başlangıç Ay/Yıl", [format_month(m) for m in all_months], index=start_default
    )

with col3:
    end_default = get_month_index("2023-09")
    end_mo = st.selectbox(
        "Bitiş Ay/Yıl", [format_month(m) for m in all_months], index=end_default
    )

start_year, start_month = map(int, start_mo.split("-"))
end_year, end_month = map(int, end_mo.split("-"))
start_filter = date(start_year, start_month, 1)
end_day = calendar.monthrange(end_year, end_month)[1]
end_filter = date(end_year, end_month, end_day)

if start_filter > end_filter:
    st.warning("Başlangıç ayı, bitiş ayından sonra. Tarihler değiştirildi.")
    start_filter, end_filter = end_filter, start_filter

# --- Park bazında filtreleme ---
if selected_park == "ÇANKAYA":
    park_df = invoice_df.copy()
else:
    park_df = invoice_df[invoice_df["name"] == selected_park]

filtered_df = park_df[
    (park_df["start_read_date"] >= start_filter)
    & (park_df["end_read_date"] <= end_filter)
].copy()

filtered_df["difference_pct"] = (
    ((filtered_df["difference"] / filtered_df["estimated_volume"]) * 100)
    .replace([float("inf"), float("-inf")], 0)
    .fillna(0)
)

display_df = filtered_df.drop(columns=["grass_area"]).rename(
    columns={
        "name": "Park Adı",
        "start_read_date": "Başlangıç Tarihi",
        "end_read_date": "Bitiş Tarihi",
        "volume": "Gerçek (m³)",
        "estimated_volume": "Tahmin (m³)",
        "difference": "Fark (m³)",
        "difference_pct": "Fark (%)",
    }
)
display_df = display_df.sort_values("Bitiş Tarihi", ascending=False)

total_actual = filtered_df["volume"].sum()
total_estimated = filtered_df["estimated_volume"].sum()
total_diff = filtered_df["difference"].sum()
invoice_count = len(filtered_df)
variance_percent = (total_diff / total_estimated * 100) if total_estimated != 0 else 0

if selected_park == "ÇANKAYA":
    unique_parks_all = invoice_df.drop_duplicates(subset="name")
    grass_area_total = unique_parks_all["grass_area"].sum()
else:
    unique_park = invoice_df[invoice_df["name"] == selected_park].drop_duplicates(
        subset="name"
    )
    grass_area_total = unique_park["grass_area"].iloc[0] if not unique_park.empty else 0

# -- Tabs for the Dashboard --
tab1, tab2 = st.tabs(["Genel Bakış", "Faturalar"])

# ---------- TAB 1: Genel Bakış ----------
with tab1:
    # KPI Metrics in card-styled containers (they pick up the CSS defined above)
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.metric("Toplam Tüketim (m³)", f"{total_actual:,}", help="Gerçek su tüketimi")
    with kpi_cols[1]:
        st.metric(
            "Toplam Su İhtiyacı (m³)",
            f"{total_estimated:,}",
            help="Tahmini su ihtiyacı",
        )
    with kpi_cols[2]:
        st.metric(
            "Toplam Fark (m³)", f"{total_diff:,}", help=f"{variance_percent:.1f}% sapma"
        )
    with kpi_cols[3]:
        st.metric(
            "Toplam Yeşil Alan (m²)",
            f"{grass_area_total:,}",
            help="Seçilen parkın toplam yeşil alanı",
        )
    with kpi_cols[4]:
        st.metric("Fatura Sayısı", f"{invoice_count:,}", help="Analiz edilen kayıtlar")

    # Build the Altair time-series chart (its container is styled as a card)
    chart_df = filtered_df.copy()
    chart_df["start_read_date"] = pd.to_datetime(chart_df["start_read_date"])
    chart_df["end_read_date"] = pd.to_datetime(chart_df["end_read_date"])

    rows = []
    for _, row in chart_df.iterrows():
        start = row["start_read_date"]
        end = row["end_read_date"]
        days_in_invoice = (end - start).days + 1
        if days_in_invoice <= 0:
            continue
        daily_actual = row["volume"] / days_in_invoice
        daily_estimated = row["estimated_volume"] / days_in_invoice
        current_day = start
        while current_day <= end:
            rows.append(
                {
                    "date": current_day,
                    "daily_actual": daily_actual,
                    "daily_estimated": daily_estimated,
                }
            )
            current_day += timedelta(days=1)

    df_daily = pd.DataFrame(rows)
    df_by_day = df_daily.groupby("date", as_index=False).agg(
        {"daily_actual": "sum", "daily_estimated": "sum"}
    )
    df_by_day["year_month"] = df_by_day["date"].dt.to_period("M").dt.to_timestamp()
    df_monthly = (
        df_by_day.groupby("year_month", as_index=False)
        .agg({"daily_actual": "sum", "daily_estimated": "sum"})
        .rename(
            columns={
                "daily_actual": "actual_volume",
                "daily_estimated": "estimated_volume",
            }
        )
    )
    df_monthly["month_date"] = df_monthly["year_month"]

    df_melted = df_monthly.melt(
        id_vars="month_date",
        value_vars=["actual_volume", "estimated_volume"],
        var_name="Hacim Türü",
        value_name="Hacim (m³)",
    )

    chart = (
        alt.Chart(df_melted)
        .transform_calculate(
            yeni_hacim_turu="""
            datum["Hacim Türü"] == "actual_volume" ? "Gerçek Tüketim" :
            datum["Hacim Türü"] == "estimated_volume" ? "Su İhtiyacı" :
            datum["Hacim Türü"]
            """
        )
        .mark_line(
            point=alt.OverlayMarkDef(filled=True, size=50), interpolate="monotone"
        )
        .encode(
            x=alt.X(
                "month_date:T",
                title="Tarih (Ay)",
                axis=alt.Axis(format="%Y-%m", labelAngle=-45),
            ),
            y=alt.Y("Hacim (m³):Q", title="Toplam Tüketim (m³)"),
            color=alt.Color(
                "yeni_hacim_turu:N",
                title="",
                legend=alt.Legend(
                    labelFontSize=12, titleFontSize=14, orient="top-right"
                ),
            ),
            tooltip=[
                alt.Tooltip("month_date:T", title="Tarih", format="%Y-%m"),
                alt.Tooltip("Hacim (m³)", title="Miktar", format=",.0f"),
            ],
        )
        .properties(width="container", height=400)
    )
    st.altair_chart(chart, use_container_width=True)

# ---------- TAB 2: Faturalar ----------
with tab2:
    styled_df = display_df.style.background_gradient(
        subset=["Gerçek (m³)", "Tahmin (m³)", "Fark (m³)", "Fark (%)"], cmap="coolwarm"
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
