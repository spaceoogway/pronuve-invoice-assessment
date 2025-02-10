import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
import calendar
from dateutil import rrule
from datetime import timedelta

# -- Sayfa Başlığı ve Geniş Layout --
st.set_page_config(page_title="Su Tüketimi Panosu", layout="wide")

# -- Minimal CSS: sadece arkaplan ve font --
st.markdown("""
<style>
body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    background-color: #f9f9f9;
}
</style>
""", unsafe_allow_html=True)
st.markdown(
    """
    <style>
    /* Hide Streamlit's sidebar */
    section[data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown(
    """
    <style>
    /* Hide hamburger menu, main menu, footer */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Remove extra whitespace on top & bottom */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -- Uygulama Başlığı --
# st.title("Su Tüketimi Panosu")

# -- Veri Yükleme --
invoice_df = pd.read_csv(
    "data/ca_invoice.csv",
    usecols=["name", "grass_area", "start_read_date", "end_read_date", "volume", "estimated_volume"]
)
invoice_df["volume"] = invoice_df["volume"].astype(int)
invoice_df["difference"] = invoice_df["volume"] - invoice_df["estimated_volume"]

# Tarihleri dönüştür
invoice_df["start_read_date"] = pd.to_datetime(invoice_df["start_read_date"]).dt.date
invoice_df["end_read_date"]   = pd.to_datetime(invoice_df["end_read_date"]).dt.date

invoice_df = invoice_df[invoice_df["start_read_date"] >= pd.to_datetime("2015-01-01").date()]
# Min-Max tarihler
min_date = invoice_df["start_read_date"].min()
max_date = invoice_df["start_read_date"].max()

def month_range(start_date, end_date):
    start = date(start_date.year, start_date.month, 1)
    end   = date(end_date.year, end_date.month, 1)
    months = []
    for dt in rrule.rrule(rrule.MONTHLY, dtstart=start, until=end):
        months.append(dt.date())
    return months

def format_month(dt: date) -> str:
    return dt.strftime("%Y-%m")

all_months = sorted(month_range(min_date, max_date), reverse=True)

# Yardımcı fonksiyon: YYYY-MM indeksini bul
def get_month_index(yyyy_mm: str) -> int:
    for i, m in enumerate(all_months):
        if format_month(m) == yyyy_mm:
            return i
    return 0

# -- Filtreler --
# st.subheader("Filtreler")
col1, col2, col3 = st.columns(3)

with col1:
    # Park seçimi
    unique_parks = invoice_df["name"].unique().tolist()
    if "ÇANKAYA" not in unique_parks:
        unique_parks.insert(0, "ÇANKAYA")
    park_index = unique_parks.index("ÇANKAYA")
    selected_park = st.selectbox("Park Seçiniz:", unique_parks, index=park_index)

with col2:
    # Varsayılan Başlangıç: 2010-11
    start_default = get_month_index("2016-01")
    start_mo = st.selectbox(
        "Başlangıç Ay/Yıl",
        [format_month(m) for m in all_months],
        index=start_default
    )

with col3:
    # Varsayılan Bitiş: 2023-09 (örnek)

    end_default = get_month_index("2023-09")
    end_mo = st.selectbox(
        "Bitiş Ay/Yıl",
        [format_month(m) for m in all_months],
        index=end_default,

    )

# Tarih aralığına dönüştür
start_year, start_month = map(int, start_mo.split("-"))
end_year, end_month = map(int, end_mo.split("-"))
start_filter = date(start_year, start_month, 1)
end_day = calendar.monthrange(end_year, end_month)[1]
end_filter = date(end_year, end_month, end_day)

# Eğer kullanıcı yanlış seçtiyse ters çevir
if start_filter > end_filter:
    st.warning("Başlangıç ayı, bitiş ayından sonra. Tarihler değiştirildi.")
    start_filter, end_filter = end_filter, start_filter

# -- Veri Filtreleme --
if selected_park == "ÇANKAYA":
    park_df = invoice_df.copy()
else:
    park_df = invoice_df[invoice_df["name"] == selected_park]

filtered_df = park_df[
    (park_df["start_read_date"]   >= start_filter) &
    (park_df["end_read_date"] <= end_filter)
    ].copy()

# Fark (%)
filtered_df["difference_pct"] = (
        (filtered_df["difference"] / filtered_df["estimated_volume"]) * 100
).replace([float("inf"), float("-inf")], 0).fillna(0)

# Türkçe isimlerle tablo
display_df = filtered_df.drop(columns=["grass_area"]).rename(columns={
    "name":             "Park Adı",
    "start_read_date":  "Başlangıç Tarihi",
    "end_read_date":    "Bitiş Tarihi",
    "volume":           "Gerçek (m³)",
    "estimated_volume": "Tahmin (m³)",
    "difference":       "Fark (m³)",
    "difference_pct":   "Fark (%)"
})
# Tarih sıralaması
display_df = display_df.sort_values("Bitiş Tarihi", ascending=False)

# -- KPI Hesapları --
total_actual = filtered_df["volume"].sum()
total_estimated = filtered_df["estimated_volume"].sum()
total_diff = filtered_df["difference"].sum()
invoice_count = len(filtered_df)
variance_percent = (total_diff / total_estimated * 100) if total_estimated != 0 else 0

# -- Sekmeler --
tab1, tab2 = st.tabs(["Genel Bakış", "Faturalar"])

with tab1:
    # KPI satırı
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("Toplam Tüketim (m³)", f"{total_actual:,}", help="Gerçek su tüketimi")
    with kpi_cols[1]:
        st.metric("Toplam Su İhtiyacı (m³)", f"{total_estimated:,}", help="Tahmini su ihtiyacı")
    with kpi_cols[2]:
        st.metric("Toplam Fark (m³)", f"{total_diff:,}", help=f"{variance_percent:.1f}% sapma")
    with kpi_cols[3]:
        st.metric("Fatura Sayısı", f"{invoice_count}", help="Analiz edilen kayıtlar")

    # st.markdown("---")
    # st.subheader("Tüketim Karşılaştırma Grafiği")

    # Altair grafiği için hazırlık
    # chart_df = filtered_df.copy()
    # chart_df["Fatura Dönemi"] = (
    #         chart_df["start_read_date"].astype(str) + " - " + chart_df["end_read_date"].astype(str)
    # )
    # chart_df["start_read_datetime"] = pd.to_datetime(chart_df["start_read_date"])
    #
    # # Melt
    # chart_data = chart_df.melt(
    #     id_vars=["Fatura Dönemi", "start_read_datetime", "name"],
    #     value_vars=["volume", "estimated_volume"],
    #     var_name="Hacim Türü",
    #     value_name="Hacim (m³)"
    # )
    # sorted_periods = (
    #     chart_df.sort_values("start_read_datetime", ascending=False)["Fatura Dönemi"]
    #     .unique()
    #     .tolist()
    # )
    #
    # bar_chart = (
    #     alt.Chart(chart_data)
    #     .mark_bar()
    #     .encode(
    #         y=alt.Y("Fatura Dönemi:N", sort=sorted_periods, title="Fatura Dönemi"),
    #         x=alt.X("Hacim (m³):Q", title="Tüketim (m³)"),
    #         color=alt.Color("Hacim Türü:N", title="Hacim Türü"),
    #         tooltip=[
    #             alt.Tooltip("name", title="Park Adı"),
    #             alt.Tooltip("start_read_datetime", title="Başlangıç Tarihi"),
    #             alt.Tooltip("Fatura Dönemi", title="Dönem"),
    #             alt.Tooltip("Hacim Türü", title="Tür"),
    #             alt.Tooltip("Hacim (m³)", title="Hacim")
    #         ]
    #     )
    #     .properties(width="container", height=450)
    #     .configure_axis(labelFontSize=11)
    # )
    #
    # st.altair_chart(bar_chart, use_container_width=True)
    # 1) Group by month to reduce clutter
    # df_monthly = filtered_df.copy()
    # df_monthly["year_month"] = pd.to_datetime(df_monthly["start_read_date"]).dt.strftime("%Y-%m")
    #
    # # Sum up actual & estimated volumes per month
    # grouped = (
    #     df_monthly.groupby("year_month", as_index=False)
    #     .agg({
    #         "volume": "sum",
    #         "estimated_volume": "sum"
    #     })
    # )
    #
    # # 2) Convert to a “long” (melted) format for Altair
    # grouped_melt = grouped.melt(
    #     id_vars="year_month",
    #     value_vars=["volume", "estimated_volume"],
    #     var_name="Hacim Türü",
    #     value_name="Hacim (m³)"
    # )
    #
    # # 3) Create a grouped bar chart
    # chart = (
    #     alt.Chart(grouped_melt)
    #     .mark_bar()
    #     .encode(
    #         # Treat year_month as an ordinal category on the X axis
    #         x=alt.X(
    #             "year_month:O",
    #             sort="ascending",
    #             title="Ay/Yıl",
    #             axis=alt.Axis(labelAngle=-45)  # Slightly rotate labels to avoid overlap
    #         ),
    #         y=alt.Y(
    #             "Hacim (m³):Q",
    #             stack=None,  # This key disables stacking => side-by-side bars
    #             title="Toplam Tüketim (m³)"
    #         ),
    #         color=alt.Color(
    #             "Hacim Türü:N",
    #             title="Hacim Türü",
    #             # You can add a custom color scale if you like:
    #             # scale=alt.Scale(domain=["volume","estimated_volume"], range=["#4C78A8","#F58518"])
    #         ),
    #         tooltip=[
    #             alt.Tooltip("year_month", title="Ay/Yıl"),
    #             alt.Tooltip("Hacim Türü", title="Tür"),
    #             alt.Tooltip("Hacim (m³)", title="Toplam")
    #         ]
    #     )
    #     .properties(
    #         width="container",
    #         height=400  # Adjust as you like
    #     )
    #     .configure_axis(labelFontSize=11)
    # )
    #
    # # Then display in your Streamlit app:
    # st.altair_chart(chart, use_container_width=True)
    # Example monthly grouping
    # 2) Disaggregate each invoice into a daily usage:
    chart_df = filtered_df.copy()
    chart_df["start_read_date"] = pd.to_datetime(chart_df["start_read_date"])
    chart_df["end_read_date"]   = pd.to_datetime(chart_df["end_read_date"])

    rows = []
    for _, row in chart_df.iterrows():
        start = row["start_read_date"]
        end   = row["end_read_date"]
        days_in_invoice = (end - start).days + 1
        if days_in_invoice <= 0:
            continue

        # daily usage
        daily_actual = row["volume"] / days_in_invoice
        daily_estimated = row["estimated_volume"] / days_in_invoice

        # For each day in [start, end], build a record
        current_day = start
        while current_day <= end:
            rows.append({
                "date": current_day,
                "daily_actual": daily_actual,
                "daily_estimated": daily_estimated
            })
            current_day += timedelta(days=1)

    # Create a DataFrame with daily rows
    df_daily = pd.DataFrame(rows)

    # 3) Sum across all overlapping invoices per day
    df_by_day = (
        df_daily
        .groupby("date", as_index=False)
        .agg({
            "daily_actual": "sum",
            "daily_estimated": "sum"
        })
    )

    # 4) Optionally group by month (or keep daily). We'll group by month:
    df_by_day["year_month"] = df_by_day["date"].dt.to_period("M").dt.to_timestamp()
    df_monthly = (
        df_by_day
        .groupby("year_month", as_index=False)
        .agg({
            "daily_actual": "sum",
            "daily_estimated": "sum"
        })
        .rename(columns={
            "daily_actual": "actual_volume",
            "daily_estimated": "estimated_volume"
        })
    )

    # 5) Plot a time series on a true time scale
    #    We'll create a date column for Altair, e.g. the 1st of each month
    df_monthly["month_date"] = df_monthly["year_month"]

    # Melt to long format for Altair
    df_melted = df_monthly.melt(
        id_vars="month_date",
        value_vars=["actual_volume", "estimated_volume"],
        var_name="Hacim Türü",
        value_name="Hacim (m³)"
    )

    # Build your chart - let's do lines so partial overlaps
    # become a smooth time series
    chart = (
        alt.Chart(df_melted)
        .transform_calculate(
            yeni_hacim_turu="""
        datum["Hacim Türü"] == "actual_volume" ? "Gerçek Tüketim" :
        datum["Hacim Türü"] == "estimated_volume" ? "Su İhtiyacı" :
        datum["Hacim Türü"]
        """
        )
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=50), interpolate="monotone")
        .encode(
            x=alt.X("month_date:T", title="Tarih (Ay)", axis=alt.Axis(format="%Y-%m", labelAngle=-45)),
            y=alt.Y("Hacim (m³):Q", title="Toplam Tüketim (m³)"),
            color=alt.Color(
                "yeni_hacim_turu:N",
                title="",
                legend=alt.Legend(
                    labelFontSize=12,   # smaller label text
                    titleFontSize=14,   # smaller title text
                    orient="top-right"  # change legend position if desired
                )
            ),
            tooltip=[
                alt.Tooltip("month_date:T", title="Tarih", format="%Y-%m"),
                alt.Tooltip("Hacim (m³)", title="Miktar", format=",.0f")
            ]
        )
        .properties(width="container", height=400)
    )

    st.altair_chart(chart, use_container_width=True)

with tab2:
    # st.subheader("Fatura Kayıtları")
    # Renkli arkaplan sadece Fark (%) üzerinde
    styled_df = display_df.style.background_gradient(subset=["Gerçek (m³)", "Tahmin (m³)","Fark (m³)","Fark (%)"], cmap='coolwarm')
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    # st.dataframe(display_df.set_index("Park Adı").style.background_gradient(subset=["Fark (m³)", "Fark (%)"], cmap='coolwarm'), use_container_width=True)