import calendar
import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta
from dateutil import rrule
import geemap.foliumap as geemap
import utils

# Make sure this is the very first Streamlit call for wide layout!
st.set_page_config(page_title="Su Tüketimi Panosu", layout="wide")

# Import and inject custom CSS styling.
from style import inject_css, inject_logo
inject_css()

# Initialize Earth Engine for the satellite functionality
utils.initialize_ee()

# -----------------------
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
invoice_df["end_read_date"]   = pd.to_datetime(invoice_df["end_read_date"]).dt.date
invoice_df = invoice_df[invoice_df["start_read_date"] >= pd.to_datetime("2015-01-01").date()]

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

def get_month_index(yyyy_mm: str) -> int:
    for i, m in enumerate(all_months):
        if format_month(m) == yyyy_mm:
            return i
    return 0

# -- Top Row: Logo and Selection Controls --
col_logo, col1, col2, col3 = st.columns([1, 3, 3, 3])
with col_logo:
    inject_logo()
with col1:
    unique_parks = invoice_df["name"].unique().tolist()
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
    unique_park = invoice_df[invoice_df["name"] == selected_park].drop_duplicates(subset="name")
    grass_area_total = unique_park["grass_area"].iloc[0] if not unique_park.empty else 0

grass_area_total = int(grass_area_total)

# --- Create Dummy Penman–Monteith Data for Vegetation Calculations ---
# (These values represent the base water usage per m² for crop coefficient 1)
df_penman = pd.read_csv("data/final/daily_water_need_kc_0_8.csv")[["date", "water_need_m3"]]
df_penman["date"] = pd.to_datetime(df_penman["date"]).dt.date
df_penman = df_penman[(df_penman['date'] >= start_filter) & (df_penman['date'] <= end_filter)]
peak_water_per_m2 = df_penman["water_need_m3"].max()  # Base peak (for Kc=1)
total_water_per_m2_interval = df_penman["water_need_m3"].sum()

# --- Update Tabs to Include the New Pages ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Genel Bakış", "Faturalar", "Kötü Performans", "Su İsrafı",
    "Vegetasyon Su Tüketimi", "Park Su Kapasitesi", "Harita"
])

##############################################
#           Tab 1: Genel Bakış               #
##############################################
with tab1:
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.metric("Toplam Tüketim (m³)", f"{total_actual:,}", help="Gerçek su tüketimi")
    with kpi_cols[1]:
        st.metric("Toplam Su İhtiyacı (m³)", f"{total_estimated:,}", help="Tahmini su ihtiyacı")
    with kpi_cols[2]:
        st.metric("Toplam Fark (m³)", f"{total_diff:,}", help=f"{variance_percent:.1f}% sapma")
    with kpi_cols[3]:
        st.metric("Toplam Yeşil Alan (m²)", f"{grass_area_total:,}", help="Seçilen parkın toplam yeşil alanı")
    with kpi_cols[4]:
        st.metric("Fatura Sayısı", f"{invoice_count:,}", help="Analiz edilen kayıtlar")

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

        current_day = start
        while current_day <= end:
            rows.append({
                "date": current_day.date(),
                "daily_actual": daily_actual,
                "grass_area": row["grass_area"]
            })
            current_day += timedelta(days=1)

    df_daily = pd.DataFrame(rows)
    df_daily = df_daily.merge(df_penman.rename(columns={"water_need_m3":"daily_estimated"}),
                              how="left", on="date")
    df_daily["daily_estimated"] = df_daily["grass_area"] * df_daily["daily_estimated"]
    df_by_day = (
        df_daily
        .groupby("date", as_index=False)
        .agg({
            "daily_actual": "sum",
            "daily_estimated": "sum"
        })
    )
    df_by_day["date"] = pd.to_datetime(df_by_day["date"])
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
            datum["Hacim Türü"] == "actual_volume" ? "Gerçek Tüketimi" :
            datum["Hacim Türü"] == "estimated_volume" ? "Su İhtiyacı" :
            datum["Hacim Türü"]
            """
        )
        .mark_line(
            interpolate="monotone"
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

##############################################
#             Tab 2: Faturalar               #
##############################################
with tab2:
    styled_df = display_df.style.background_gradient(
        subset=["Gerçek (m³)", "Tahmin (m³)", "Fark (m³)", "Fark (%)"],
        cmap='coolwarm'
    )
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

##############################################
#         Tab 3: Kötü Performans             #
##############################################
with tab3:
    st.header("Kötü Performanslı Parklar")
    st.markdown(
        "Aşağıda, yetersiz su tüketimi ve aşırı su tüketimi performansına sahip parklar gösterilmektedir. "
        "Bu analiz için tarih filtresi uygulanmıştır; tüm parklar dikkate alınmaktadır."
    )
    worst_df = invoice_df[
        (invoice_df["start_read_date"] >= start_filter) &
        (invoice_df["end_read_date"] <= end_filter)
        ].copy()
    agg_df = worst_df.groupby("name").agg({
        "volume": "sum",
        "estimated_volume": "sum"
    }).reset_index()
    agg_df["difference"] = agg_df["volume"] - agg_df["estimated_volume"]
    agg_df["difference_pct"] = (
            (agg_df["difference"] / agg_df["estimated_volume"]) * 100
    ).replace([float("inf"), float("-inf")], 0).fillna(0)
    under_df = agg_df[agg_df["difference_pct"] < 0].copy()
    over_df = agg_df[agg_df["difference_pct"] > 0].copy()
    under_df = under_df.sort_values("difference_pct", ascending=True)
    over_df = over_df.sort_values("difference_pct", ascending=False)
    st.subheader("Yetersiz Su Tüketimi")
    if not under_df.empty:
        under_chart = alt.Chart(under_df).mark_bar().encode(
            x=alt.X("difference_pct:Q", title="Fark (%)", axis=alt.Axis(format=".2f")),
            y=alt.Y("name:N", sort=alt.SortField(field="difference_pct", order="ascending"), title="Park"),
            tooltip=[
                alt.Tooltip("name:N", title="Park"),
                alt.Tooltip("volume:Q", title="Gerçek Tüketim (m³)", format=",.0f"),
                alt.Tooltip("estimated_volume:Q", title="Tahmin (m³)", format=",.0f"),
                alt.Tooltip("difference_pct:Q", title="Fark (%)", format=".2f")
            ]
        ).properties(width=700, height=300, title="Yetersiz Su Tüketimi")
        st.altair_chart(under_chart, use_container_width=True)
    else:
        st.info("Yetersiz su tüketimi gösteren park bulunamadı.")
    st.subheader("Aşırı Su Tüketimi")
    if not over_df.empty:
        over_chart = alt.Chart(over_df).mark_bar().encode(
            x=alt.X("difference_pct:Q", title="Fark (%)", axis=alt.Axis(format=".2f")),
            y=alt.Y("name:N", sort=alt.SortField(field="difference_pct", order="descending"), title="Park"),
            tooltip=[
                alt.Tooltip("name:N", title="Park"),
                alt.Tooltip("volume:Q", title="Gerçek Tüketim (m³)", format=",.0f"),
                alt.Tooltip("estimated_volume:Q", title="Tahmin (m³)", format=",.0f"),
                alt.Tooltip("difference_pct:Q", title="Fark (%)", format=".2f")
            ]
        ).properties(width=700, height=300, title="Aşırı Su Tüketimi")
        st.altair_chart(over_chart, use_container_width=True)
    else:
        st.info("Aşırı su tüketimi gösteren park bulunamadı.")

##############################################
#          Tab 4: Su İsrafı (Wasted Water)   #
##############################################
with tab4:
    st.header("Park'ta Su İsrafı Maliyeti")
    st.markdown(
        "Sadece su israfına yol açan (gerçek tüketim > tahmin) faturalar dikkate alınmıştır. "
        "Atık su maliyeti, su fazlası miktarının 20 TL/m³ ile çarpılmasıyla hesaplanır."
    )
    wasted_df = filtered_df[filtered_df["difference"] > 0].copy()
    if wasted_df.empty:
        st.info("İlgili tarihlerde su israfına ilişkin bir fatura bulunmamaktadır.")
    else:
        wasted_df["wasted_tl"] = wasted_df["difference"] * 20
        total_wasted_tl = wasted_df["wasted_tl"].sum()
        st.metric("Toplam Su İsrafı Maliyeti (TL)", f"{total_wasted_tl:,.0f}")

        wasted_df["end_read_date"] = pd.to_datetime(wasted_df["end_read_date"])
        wasted_df["year_month"] = wasted_df["end_read_date"].dt.to_period("M").dt.to_timestamp()
        wasted_group = wasted_df.groupby("year_month", as_index=False).agg({"wasted_tl": "sum"})

        chart_waste = alt.Chart(wasted_group).mark_bar(color="red").encode(
            x=alt.X("year_month:T", title="Tarih (Ay)", axis=alt.Axis(format="%Y-%m", labelAngle=-45)),
            y=alt.Y("wasted_tl:Q", title="Su İsrafı Maliyeti (TL)"),
            tooltip=[
                alt.Tooltip("year_month:T", title="Tarih", format="%Y-%m"),
                alt.Tooltip("wasted_tl:Q", title="Maliyet (TL)", format=",.0f")
            ]
        ).properties(width=700, height=400)

        st.altair_chart(chart_waste, use_container_width=True)

##############################################
#       Tab 5: bitki Su Tüketimi         #
##############################################
with tab5:
    st.header("Bitki Su Tüketimi Hesaplamaları")
    st.markdown(
        """
        Bu bölümde; 
        - Farklı bitki türlerinin adı, alanı (m²) ve mahsul katsayısı girilir.
        - Seçilen tarih aralığı için Penman–Monteith hesaplamalarından elde edilen 
          (katsayı=1) günlük su ihtiyacına göre, her bitki için günlük ve toplam su kullanımı hesaplanır.
        - Ayrıca su maliyeti (20 TL/m³) ve günlük veriler grafiklerle gösterilir.
        """
    )
    # (Optional) Display a sample image to enhance the UI

    # Initialize the vegetation list in session_state
    if "vegetations" not in st.session_state:
        st.session_state["vegetations"] = []

    st.subheader("Bitki Bilgilerini Ekle")
    with st.form("add_vegetation_form"):
        veg_name = st.text_input("Bitki Adı")
        veg_area = st.number_input("Alan (m²)", min_value=0.0, value=0.0, step=1.0)
        crop_coeff = st.number_input("Mahsul Katsayısı", min_value=0.0, value=1.0, step=0.1)
        submitted = st.form_submit_button("Ekle")
        if submitted:
            if veg_name and veg_area > 0:
                st.session_state["vegetations"].append({
                    "name": veg_name,
                    "area": veg_area,
                    "crop_coeff": crop_coeff
                })
                st.success(f"{veg_name} eklendi.")
            else:
                st.error("Lütfen geçerli bir bitki adı ve alanı giriniz.")

    if st.session_state["vegetations"]:
        veg_df = pd.DataFrame(st.session_state["vegetations"])
        st.dataframe(veg_df, use_container_width=True)
    else:
        st.info("Henüz bitki eklenmedi.")

    # Only calculate if at least one vegetation has been added.
    if st.session_state["vegetations"]:
        # Calculate per-vegetation peak and total water usage
        veg_usage = []
        for veg in st.session_state["vegetations"]:
            veg_peak = peak_water_per_m2 * veg["crop_coeff"] * veg["area"]
            veg_total = total_water_per_m2_interval * veg["crop_coeff"] * veg["area"]
            veg_usage.append({
                "Bitki": veg["name"],
                "Alan (m²)": veg["area"],
                "Mahsul Katsayısı": veg["crop_coeff"],
                "Günlük Tepe Kullanım (m³)": veg_peak,
                "Toplam Kullanım (m³)": veg_total
            })
        usage_df = pd.DataFrame(veg_usage)
        st.subheader("bitki Bazında Su Kullanım Bilgileri")
        st.dataframe(usage_df, use_container_width=True)

        # Overall totals
        total_water_usage = sum( total_water_per_m2_interval * veg["crop_coeff"] * veg["area"] for veg in st.session_state["vegetations"] )
        total_cost = total_water_usage * 20



        # Compute daily time-series based on the dummy penman–monteith data
        df_daily_usage = df_penman.copy()
        # For each day, add the water usage from each vegetation
        df_daily_usage["total_water_usage"] = 0
        for veg in st.session_state["vegetations"]:
            df_daily_usage["total_water_usage"] += df_daily_usage["water_need_m3"] * veg["crop_coeff"] * veg["area"]
        df_daily_usage["total_cost"] = df_daily_usage["total_water_usage"] * 20

        # Display peak daily water usage
        peak_daily_usage = df_daily_usage["total_water_usage"].max()

        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.metric("Toplam Su Kullanımı (m³)", f"{total_water_usage:,.2f}")
        with kpi_cols[1]:
            st.metric("Toplam Su Maliyeti (TL)", f"{total_cost:,.2f}")
        with kpi_cols[2]:
            st.metric("Günlük En Yüksek Su Kullanımı (m³)", f"{peak_daily_usage:,.2f}")


        # Line chart for daily cost
        cost_chart = alt.Chart(df_daily_usage).mark_line(color="orange").encode(
            x=alt.X("date:T", title="Tarih"),
            y=alt.Y("total_cost:Q", title="Günlük Su Maliyeti (TL)"),
            tooltip=[
                alt.Tooltip("date:T", title="Tarih", format="%Y-%m-%d"),
                alt.Tooltip("total_cost:Q", title="Maliyet (TL)", format=",.2f")
            ]
        ).properties(width="container", height=300, title="Günlük Su Maliyeti")
        st.altair_chart(cost_chart, use_container_width=True)

        # Line chart for daily water volume
        vol_chart = alt.Chart(df_daily_usage).mark_line(color="blue").encode(
            x=alt.X("date:T", title="Tarih"),
            y=alt.Y("total_water_usage:Q", title="Günlük Su Kullanımı (m³)"),
            tooltip=[
                alt.Tooltip("date:T", title="Tarih", format="%Y-%m-%d"),
                alt.Tooltip("total_water_usage:Q", title="Kullanım (m³)", format=",.2f")
            ]
        ).properties(width="container", height=300, title="Günlük Su Kullanımı")
        st.altair_chart(vol_chart, use_container_width=True)

##############################################
#         Tab 6: Park Su Kapasitesi          #
##############################################
with tab6:
    st.header("Park Su Kapasitesi ve Vegetasyon Ek Alan Hesabı")
    st.markdown(
        """
        Bu bölümde:
        - Parkın toplam alanı, su akış kapasitesi (m³/gün) ve su deposu hacmi (m³) girilir.
        - Farklı vegetasyon türleri için mevcut alan tahsisleri slider ile ayarlanır.
        - Mevcut tahsisin yanında, su akış kapasitesi ve depo hacmi göz önüne alınarak,
          eklenebilecek maksimum vegetasyon alanı hesaplanır.
        """
    )

    st.subheader("Giriş Bilgileri")
    park_area = st.number_input("Park Alanı (m²)", min_value=0.0, value=1000.0, step=10.0)
    water_flow = st.number_input("Su Akış Kapasitesi (m³/gün)", min_value=0.0, value=500.0, step=10.0)
    tank_volume = st.number_input("Su Deposu Hacmi (m³)", min_value=0.0, value=1000.0, step=10.0)

    st.subheader("Mevcut Vegetasyon Alanı Tahsisi")
    # For simplicity, here we assume three farklı vegetasyon türü.
    veg_a = st.slider("Vegetasyon A Alanı (m²)", 0, int(park_area), 0)
    veg_b = st.slider("Vegetasyon B Alanı (m²)", 0, int(park_area), 0)
    veg_c = st.slider("Vegetasyon C Alanı (m²)", 0, int(park_area), 0)
    current_veg_area = veg_a + veg_b + veg_c

    # Su temininde sınırlayıcı olan faktör: depodaki su ve akış kapasitesi
    available_water = water_flow + tank_volume
    # Su kullanımında kritik parametre: peak_water_per_m2 (m³/m²/gün)
    # Bu değere göre, sistemin günde destekleyebileceği maksimum vegetasyon alanı:
    water_based_limit_area = available_water / peak_water_per_m2

    # Eklenebilecek maksimum alan;
    # hem parkta kalan alan hem de suya göre desteklenebilecek alan dikkate alınır.
    remaining_area = max(park_area - current_veg_area, 0)
    additional_area_possible = max(water_based_limit_area - current_veg_area, 0)
    max_additional_area = min(remaining_area, additional_area_possible)

    st.subheader("Hesaplama Sonucu")
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("Mevcut Toplam Vegetasyon Alanı (m²)", f"{current_veg_area}")
    with kpi_cols[1]:
        st.metric("Parkta Kalan Alan (m²)", f"{remaining_area}")
    with kpi_cols[2]:
        st.metric("Su Temelli Maksimum Desteklenebilen Alan (m²)", f"{water_based_limit_area:.0f}")
    with kpi_cols[3]:
        st.metric("Eklenebilecek Maksimum Vegetasyon Alanı (m²)", f"{max_additional_area:.0f}")


    # Optionally, show a bar chart comparing these values.
    data = pd.DataFrame({
        "Kategori": ["Mevcut Tahsis", "Kalan Park Alanı", "Su Destek Limiti", "Eklenebilecek Alan"],
        "Alan (m²)": [current_veg_area, remaining_area, water_based_limit_area, max_additional_area]
    })
    bar_chart = alt.Chart(data).mark_bar().encode(
        x=alt.X("Kategori:N", title=""),
        y=alt.Y("Alan (m²):Q", title="Alan (m²)"),
        color=alt.Color("Kategori:N")
    ).properties(width="container", height=300)
    st.altair_chart(bar_chart, use_container_width=True)

##############################################
#           Tab 7: Harita (Map)              #
##############################################
with tab7:

    map_col1, map_col2 = st.columns([1, 3])

    with map_col1:
        st.subheader("Harita Ayarları")

        # Load park polygons for the search functionality
        park_gdf = utils.load_csv_polygons("data/park_polygons.csv")
        park_names = ["Seçiniz..."] + sorted(park_gdf["name"].unique().tolist())

        # Park search functionality
        selected_park = st.selectbox("Park Ara:", park_names)

        # Date selection for satellite imagery
        st.subheader("Tarih Seçimi")
        start_date_map = st.date_input(
            "Başlangıç Tarihi",
            value=date(2023, 6, 1),
            min_value=date(2000, 1, 1),
            max_value=date(2024, 12, 31)
        )

        end_date_map = st.date_input(
            "Bitiş Tarihi",
            value=date(2023, 6, 28),
            min_value=date(2000, 1, 1),
            max_value=date(2024, 12, 31)
        )

        if start_date_map > end_date_map:
            st.warning("Başlangıç tarihi, bitiş tarihinden sonra olamaz.")
            start_date_map, end_date_map = end_date_map, start_date_map



    with map_col2:
        # Default center and buffer
        center = [39.9052, 32.8112]  # Default: Ankara coordinates
        zoom_level = 12
        buffer = 0.02  # Default buffer

        # Determine map center and bounds based on selected park
        if selected_park != "Seçiniz...":
            # Get the park geometry
            selected_park_geom = park_gdf[park_gdf["name"] == selected_park].iloc[0]["geometry"]

            # Get the centroid for the AOI creation
            center = [selected_park_geom.centroid.y, selected_park_geom.centroid.x]

            # Calculate a tighter buffer based on park size
            minx, miny, maxx, maxy = selected_park_geom.bounds
            width = maxx - minx
            height = maxy - miny
            buffer = max(width, height) * 0.5  # Buffer based on park size

            # Set a closer zoom level
            zoom_level = 15

        # Create AOI for satellite image
        aoi = utils.create_aoi(center, buffer)

        # Format dates for API
        start_date_str = start_date_map.strftime("%Y-%m-%d")
        end_date_str = end_date_map.strftime("%Y-%m-%d")

        # Get satellite image
        image = utils.get_satellite_image(aoi, start_date_str, end_date_str)

        # Compute ndvi of the image
        ndvi = utils.compute_ndvi(image)

        # Create map with the selected layers
        m = utils.create_map_with_layers(center, zoom_level)

        # Add park polygons to the map and return parks union
        # This function now handles map bounds adjustment
        parks_union = utils.add_park_polygons(m, "data/park_polygons.csv", selected_park)

        m = utils.add_ndvi_layer(m, parks_union, ndvi)

        # Add layer control
        m.addLayerControl()

        # Put the map to streamlit
        m.to_streamlit(height=670)

if __name__ == "__main__":
    pass  # Main execution happens above