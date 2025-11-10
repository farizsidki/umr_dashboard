import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# CONFIG
st.set_page_config(page_title="Indonesia Minimum Wage Dashboard", layout="wide")
st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
st.title("Indonesia Regional Minimum Wage (UMR) Dashboard")

# === CUSTOM CSS ===
st.markdown("""
<style>
/* Umum */
div.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

/* Card styling */
.card {
    background-color: #FFFFFF;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 25px;
}

/* Judul antar bagian */
h3, h4, h2 {
    margin-top: 0;
}

/* Lebih rapat di layout kolom */
.css-ocqkz7, .css-1r6slb0 {
    margin-bottom: 0 !important;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""

<style>
/* Ratakan tinggi kolom */
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}
</style>
""", unsafe_allow_html=True)


# LOAD DATA
DATA_PATH = "umr.xlsx"

@st.cache_data
def load_data(path=DATA_PATH):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip().str.upper()
    expected = ["REGION", "SALARY", "YEAR"]
    for e in expected:
        if e not in df.columns:
            raise ValueError(f"Column '{e}' not found in {path}. Ensure the column exists and is named {expected}.")
    df["REGION"] = df["REGION"].astype(str).str.strip()
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce").astype("Int64")
    df["SALARY"] = pd.to_numeric(df["SALARY"], errors="coerce")
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# SIDEBAR FILTERS
st.sidebar.header("Data Filters")

min_year, max_year = int(df["YEAR"].min()), int(df["YEAR"].max())
year_range = st.sidebar.slider(
    "Select Year or Year Range",
    min_year, max_year, (max_year, max_year)
)
year_from, year_to = year_range

prov_list = sorted(df[df["REGION"].str.upper() != "INDONESIA"]["REGION"].unique())
total_prov = len(prov_list)

st.sidebar.subheader("Select Provinces")
select_all = st.sidebar.checkbox("Select All (ALL)", value=True)

if select_all:
    selected_prov = prov_list.copy()
else:
    selected_prov = st.sidebar.multiselect("Search and select provinces", options=prov_list, default=[])

include_indonesia = st.sidebar.checkbox("Show National Average (INDONESIA)", value=True)

top_bottom_n = st.sidebar.slider("Number of Top/Bottom", 1, max(1, total_prov), min(5, max(1, total_prov)))

# APPLY YEAR FILTER
if year_from == year_to:
    df_year = df[df["YEAR"] == year_from].copy()
else:
    df_year = df[(df["YEAR"] >= year_from) & (df["YEAR"] <= year_to)].copy()

# PREPARE NATIONAL & PROV DATA
df_national = df_year[df_year["REGION"].str.upper() == "INDONESIA"].copy()

if not selected_prov:
    selected_prov = prov_list.copy()

df_prov = df_year[df_year["REGION"].isin(selected_prov)].copy()
df_prov = df_prov[df_prov["REGION"].str.upper() != "INDONESIA"].copy()

if df_year.empty:
    st.warning("No data available for the selected year range")
    st.stop()

# KPI UTAMA (4 metrics)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader(f"Key KPIs ({year_from}–{year_to})")
k1, k2, k3, k4 = st.columns(4)

# 1. Nasional tertinggi (REGION=INDONESIA)
if not df_national.empty:
    idx_max_nat = df_national["SALARY"].idxmax()
    row_max_nat = df_national.loc[idx_max_nat]
    k1.metric(
        label="Highest National Average UMR",
        value=f"Rp {int(row_max_nat['SALARY']):,}",
        delta=f"Year {int(row_max_nat['YEAR'])}"
    )
else:
    k1.metric("Highest National Average UMR", "Not available")

# 2. Nasional terendah (REGION=INDONESIA)
if not df_national.empty:
    idx_min_nat = df_national["SALARY"].idxmin()
    row_min_nat = df_national.loc[idx_min_nat]
    k2.metric(
        label="Lowest National Average UMR",
        value=f"Rp {int(row_min_nat['SALARY']):,}",
        delta=f"Year {int(row_min_nat['YEAR'])}"
    )
else:
    k2.metric("Lowest National Average UMR", "Not available")

# 3. Provinsi tertinggi (exclude INDONESIA)
if not df_prov.empty:
    idx_max_prov = df_prov["SALARY"].idxmax()
    row_max_prov = df_prov.loc[idx_max_prov]
    k3.metric(
        label="Highest Provincial UMR",
        value=f"Rp {int(row_max_prov['SALARY']):,}",
        delta=f"{row_max_prov['REGION']} ({int(row_max_prov['YEAR'])})"
    )
else:
    k3.metric("Highest Provincial UMR", "Not available")

# 4. Provinsi terendah (exclude INDONESIA)
if not df_prov.empty:
    idx_min_prov = df_prov["SALARY"].idxmin()
    row_min_prov = df_prov.loc[idx_min_prov]
    k4.metric(
        label="Lowest Provincial UMR",
        value=f"Rp {int(row_min_prov['SALARY']):,}",
        delta=f"{row_min_prov['REGION']} ({int(row_min_prov['YEAR'])})"
    )
else:
    k4.metric("Lowest Provincial UMR", "Not available")
st.markdown('</div>', unsafe_allow_html=True)

# PETA INTERAKTIF UMR PER PROVINSI
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Interactive Map of UMR in Indonesia")

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/superpikar/indonesia-geojson/master/indonesia-province-simple.json"
    r = requests.get(url)
    return r.json()

geojson = load_geojson()

# Ambil hanya level provinsi (tanpa 'INDONESIA')
df_prov = df[df["REGION"].str.upper() != "INDONESIA"].copy()

# Filter sesuai slider tahun
df_filtered = df_prov[(df_prov["YEAR"] >= year_from) & (df_prov["YEAR"] <= year_to)].copy()

# Pastikan semua provinsi tetap muncul
all_prov = sorted(df_prov["REGION"].unique())
base = pd.DataFrame({"REGION": all_prov})

# Ambil nilai tahun terakhir untuk warna peta
df_latest = (
    df_filtered.sort_values("YEAR")
    .groupby("REGION", as_index=False)
    .last()[["REGION", "SALARY"]]
)

# Gabungkan agar semua provinsi muncul
df_map = base.merge(df_latest, on="REGION", how="left").fillna(0)

# Tooltip data: gabungkan seluruh tahun dalam rentang filter
tooltip_data = (
    df_filtered.sort_values(["REGION", "YEAR"])
    .groupby("REGION")
    .apply(lambda g: "<br>".join(
        [f"{int(y)}: Rp {int(s):,}" for y, s in zip(g["YEAR"], g["SALARY"])]
    ))
    .reset_index(name="DETAIL_UMR")
)

df_map = df_map.merge(tooltip_data, on="REGION", how="left")
df_map["DETAIL_UMR"] = df_map["DETAIL_UMR"].fillna("No data available for the selected year range")

df_map["CUSTOM_HOVER"] = df_map["REGION"] + "<br><br>" + df_map["DETAIL_UMR"]

color_scale = "YlGnBu"

# Buat peta
fig_map = px.choropleth_mapbox(
    df_map,
    geojson=geojson,
    featureidkey="properties.Propinsi",
    locations="REGION",
    color="SALARY",
    color_continuous_scale=color_scale,
    mapbox_style="carto-positron",
    center={"lat": -2.5, "lon": 118},
    zoom=3.8,
    opacity=0.85,
    title=f"Indonesia UMR Map ({year_from}–{year_to})"
)

fig_map.update_traces(
    customdata=df_map[["CUSTOM_HOVER"]],
    hovertemplate="%{customdata[0]}<extra></extra>"
)

fig_map.update_layout(
    margin=dict(l=10, r=10, t=50, b=10),
    height=600,
    coloraxis_colorbar=dict(title="UMR (Rp)")
)

st.plotly_chart(fig_map, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# TOP & BOTTOM N PROVINSI
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Top & Bottom {top_bottom_n} by Actual UMR Value ({year_from}–{year_to})")

prov_filtered = df[
    (df["YEAR"] >= year_from) & 
    (df["YEAR"] <= year_to) & 
    (df["REGION"].isin(selected_prov + ["INDONESIA"]))
].copy()

if prov_filtered.empty:
    st.warning("No data matching the filters")
    st.stop()

top_df = prov_filtered.nlargest(top_bottom_n, "SALARY").reset_index(drop=True)
bot_df = prov_filtered.nsmallest(top_bottom_n, "SALARY").reset_index(drop=True)

top_df["LABEL"] = top_df.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)
bot_df["LABEL"] = bot_df.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)

top_df["SALARY"] = pd.to_numeric(top_df["SALARY"], errors="coerce")
bot_df["SALARY"] = pd.to_numeric(bot_df["SALARY"], errors="coerce")

# Tampilkan side-by-side
col_top, col_bot = st.columns(2)

with col_top:
    st.markdown(f"#### Top {top_bottom_n} by Actual UMR Value")
    if top_df.empty:
        st.write("No data available for Top")
    else:
        st.dataframe(
            top_df[["REGION", "SALARY", "YEAR"]]
            .assign(SALARY=top_df["SALARY"].apply(lambda x: f"Rp {int(x):,}"))
            .style.hide(axis="index"),
            use_container_width=True
        )

        category_order_top = top_df.sort_values("SALARY", ascending=False)["LABEL"].tolist()

        fig_top = px.bar(
            top_df,
            x="SALARY",
            y="LABEL",
            orientation="h",
            text=top_df["SALARY"].map(lambda x: f"Rp {int(x):,}"),
            color="SALARY",
            color_continuous_scale="Viridis",
            labels={"SALARY": "UMR", "LABEL": "Province (Year)"},
            title=f"Top {top_bottom_n} by Actual UMR Value",
            category_orders={"LABEL": category_order_top}
        )

        fig_top.update_traces(
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=12),
            hovertemplate="Province (Year): %{y}<br>UMR: Rp %{x:,.0f}<extra></extra>"
        )

        fig_top.update_layout(
            xaxis_title="Rp",
            yaxis_title=None,
            showlegend=False
        )

        st.plotly_chart(fig_top, use_container_width=True)

with col_bot:
    st.markdown(f"#### Bottom {top_bottom_n} by Actual UMR Value")
    if bot_df.empty:
        st.write("No data available for Bottom")
    else:
        st.dataframe(
            bot_df[["REGION", "SALARY", "YEAR"]]
            .assign(SALARY=bot_df["SALARY"].apply(lambda x: f"Rp {int(x):,}"))
            .style.hide(axis="index"),
            use_container_width=True
        )

        category_order_bot = bot_df.sort_values("SALARY", ascending=True)["LABEL"].tolist()

        fig_bot = px.bar(
            bot_df,
            x="SALARY",
            y="LABEL",
            orientation="h",
            text=bot_df["SALARY"].map(lambda x: f"Rp {int(x):,}"),
            color="SALARY",
            color_continuous_scale="Reds",
            labels={"SALARY": "UMR", "LABEL": "Province (Year)"},
            title=f"Bottom {top_bottom_n} by Actual UMR Value",
            category_orders={"LABEL": category_order_bot}
        )

        fig_bot.update_traces(
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=12),
            hovertemplate="Province (Year): %{y}<br>UMR: Rp %{x:,.0f}<extra></extra>"
        )

        fig_bot.update_layout(
            xaxis_title="Rp",
            yaxis_title=None,
            showlegend=False
        )

        st.plotly_chart(fig_bot, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# Persentase & Nominal Kenaikan UMR
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### Percentage & Nominal UMR Increase by Year")

growth_filtered = df.query(
    "YEAR >= @year_from - 1 and YEAR <= @year_to and REGION in @selected_prov"
).copy()

if include_indonesia:
    indo_data = df.query(
        "REGION.str.upper() == 'INDONESIA' and YEAR >= @year_from - 1 and YEAR <= @year_to"
    )
    growth_filtered = pd.concat([growth_filtered, indo_data], ignore_index=True)

if growth_filtered.empty:
    st.info("No data available to calculate percentage and nominal UMR increase")
else:

    growth_filtered = growth_filtered.sort_values(["REGION", "YEAR"])
    growth_filtered["PCT_CHANGE"] = growth_filtered.groupby("REGION")["SALARY"].pct_change() * 100
    growth_filtered["NOMINAL_CHANGE"] = growth_filtered.groupby("REGION")["SALARY"].diff()

    pct_df = growth_filtered[growth_filtered["YEAR"] >= year_from].dropna(subset=["PCT_CHANGE", "NOMINAL_CHANGE"]).copy()

    if pct_df.empty:
        st.info("No previous year data available to calculate growth")
    else:
        pct_df["TOOLTIP"] = (
            pct_df["REGION"] + "<br>Year: " + pct_df["YEAR"].astype(int).astype(str) +
            "<br>Increase: Rp " + pct_df["NOMINAL_CHANGE"].astype(int).map("{:,}".format) +
            " (" + pct_df["PCT_CHANGE"].round(2).astype(str) + "%)"
        )

        fig_pct = px.line(
            pct_df,
            x="YEAR",
            y="PCT_CHANGE",
            color="REGION",
            markers=True,
            labels={"YEAR": "Year", "PCT_CHANGE": "Increase (%)", "REGION": "Region"},
            title="Percentage & Nominal UMR Increase by Year"
        )

        for trace in fig_pct.data:
            region_data = pct_df[pct_df["REGION"] == trace.name]
            hover_text = region_data["TOOLTIP"].tolist()
            
            if trace.name.upper() == "INDONESIA":
                trace.update(line=dict(width=4, color="red"))
            else:
                trace.update(line=dict(width=2))
            
            trace.update(
                hovertemplate=hover_text,
                hoverlabel=dict(namelength=0)
            )

        fig_pct.update_layout(
            legend=dict(
                title=None,
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.05
            ),
            margin=dict(t=80, b=40, r=200),
            height=500,
            hovermode="closest"
        )

        fig_pct.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_pct, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# TOP & BOTTOM N PROVINSI BERDASARKAN PERSENTASE KENAIKAN
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Top & Bottom {top_bottom_n} by Percentage Increase ({year_from}–{year_to})")

prov_filtered = pct_df.copy()
if prov_filtered.empty:
    st.warning("No data matching the selected filters")
else:

    top_df = prov_filtered.nlargest(top_bottom_n, "PCT_CHANGE")[["REGION", "PCT_CHANGE", "NOMINAL_CHANGE", "YEAR"]].reset_index(drop=True)
    bot_df = prov_filtered.nsmallest(top_bottom_n, "PCT_CHANGE")[["REGION", "PCT_CHANGE", "NOMINAL_CHANGE", "YEAR"]].reset_index(drop=True)

    top_df["LABEL"] = top_df.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)
    bot_df["LABEL"] = bot_df.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)

    col_top, col_bot = st.columns(2)

    with col_top:
        st.markdown(f"#### Top {top_bottom_n} (% Increase)")
        if top_df.empty:
            st.write("No data available for Top")
        else:
            st.dataframe(
            top_df[["REGION", "PCT_CHANGE", "NOMINAL_CHANGE", "YEAR"]]
            .rename(columns={"PCT_CHANGE": "% Increase", "NOMINAL_CHANGE": "Nominal Increase (Rp)"})
            .assign(
                **{
                    "% Increase": lambda x: x["% Increase"].round(2).astype(str) + "%",
                    "Nominal Increase (Rp)": lambda x: x["Nominal Increase (Rp)"].apply(lambda y: f"Rp {int(y):,}")
                }
            )
            .style.hide(axis="index"),
            use_container_width=True
        )

            category_order_top = top_df.sort_values("PCT_CHANGE", ascending=False)["LABEL"].tolist()
            fig_top = px.bar(
                top_df,
                x="PCT_CHANGE",
                y="LABEL",
                orientation="h",
                text=top_df["PCT_CHANGE"].round(2).astype(str) + "%",
                color="PCT_CHANGE",
                color_continuous_scale="Viridis",
                labels={"PCT_CHANGE": "Increase (%)", "LABEL": "Province (Year)"},
                title=f"Top {top_bottom_n} by Percentage Increase",
                category_orders={"LABEL": category_order_top}
            )

            fig_top.update_traces(
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=12),
                hovertemplate="Province (Year): %{y}<br>Increase: %{x:.2f}%<extra></extra>"
            )

            fig_top.update_layout(xaxis_title="Increase (%)", yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_top, use_container_width=True)

    with col_bot:
        st.markdown(f"#### Bottom {top_bottom_n} (% Increase)")
        if bot_df.empty:
            st.write("No data available for Bottom % Increase")
        else:
            st.dataframe(
                bot_df[["REGION", "PCT_CHANGE", "NOMINAL_CHANGE", "YEAR"]]
                .assign(
                    PCT_CHANGE=lambda x: x["PCT_CHANGE"].round(2).astype(str) + "%",
                    NOMINAL_CHANGE=lambda x: x["NOMINAL_CHANGE"].apply(lambda y: f"Rp {int(y):,}")
                )
                .style.hide(axis="index"),
                use_container_width=True
            )

            category_order_bot = bot_df.sort_values("PCT_CHANGE", ascending=True)["LABEL"].tolist()
            fig_bot = px.bar(
                bot_df,
                x="PCT_CHANGE",
                y="LABEL",
                orientation="h",
                text=bot_df["PCT_CHANGE"].round(2).astype(str) + "%",
                color="PCT_CHANGE",
                color_continuous_scale="Reds",
                labels={"PCT_CHANGE": "Increase (%)", "LABEL": "Province (Year)"},
                title=f"Bottom {top_bottom_n} by Percentage Increase",
                category_orders={"LABEL": category_order_bot}
            )

            fig_bot.update_traces(
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=12),
                hovertemplate="Province (Year): %{y}<br>Increase: %{x:.2f}%<extra></extra>"
            )

            fig_bot.update_layout(xaxis_title="Increase (%)", yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_bot, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# HEATMAP UMR PER PROVINSI PER TAHUN
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Heatmap UMR by Year ({year_from}–{year_to})")

heatmap_regions = selected_prov.copy()
if include_indonesia:
    heatmap_regions.append("INDONESIA")

df_heat = df_year[df_year["REGION"].isin(heatmap_regions)].copy()

if df_heat.empty:
    st.info("No data available for the heatmap with the selected filters")
else:
    heat_data = df_heat.pivot_table(
        index="REGION",
        columns="YEAR",
        values="SALARY",
        aggfunc="mean"
    ).fillna(0)

    heat_data = heat_data.sort_index()

    fig_heat = px.imshow(
        heat_data,
        labels=dict(x="Year", y="Province", color="UMR (Rp)"),
        x=heat_data.columns,
        y=heat_data.index,
        color_continuous_scale="Viridis",
        text_auto=True
    )

    fig_heat.update_layout(
        height=600,
        margin=dict(t=50, b=50),
    )

    st.plotly_chart(fig_heat, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# GAP UMR PROVINSI vs NASIONAL
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Provincial UMR Gap vs National Average by Year ({year_from}–{year_to})")

df_gap = df_year[df_year["REGION"].isin(selected_prov)].copy()
df_national_avg = df_year[df_year["REGION"].str.upper() == "INDONESIA"].copy()

if df_gap.empty or df_national_avg.empty:
    st.info("No data to calculate UMR Gap")
else:
    df_gap = df_gap.merge(
        df_national_avg[["YEAR", "SALARY"]],
        on="YEAR",
        how="left",
        suffixes=("", "_NATIONAL")
    )
    df_gap["GAP"] = df_gap["SALARY"] - df_gap["SALARY_NATIONAL"]

    df_gap["STATUS"] = df_gap["GAP"].apply(
        lambda x: "Above National Average" if x > 0 else ("Equal to National Average" if x == 0 else "Below National Average")
    )

    if year_from == year_to:
        fig_gap = px.bar(
            df_gap,
            x="REGION",
            y="GAP",
            color="REGION",
            labels={
                "GAP": "UMR Gap (Rp)",
                "REGION": "Province",
                "SALARY": "UMR",
                "SALARY_NATIONAL": "National UMR"
            },
            title=f"Provincial UMR Gap vs National Average ({year_from})",
            hover_data={
                "GAP": ":,.0f",
                "SALARY": ":,.0f",
                "SALARY_NATIONAL": ":,.0f",
                "STATUS": True
            }
        )
    else:
        fig_gap = px.bar(
            df_gap,
            x="YEAR",
            y="GAP",
            color="REGION",
            barmode="group",
            labels={
                "GAP": "UMR Gap (Rp)",
                "YEAR": "Year",
                "REGION": "Province",
                "SALARY": "UMR",
                "SALARY_NATIONAL": "National UMR"
            },
            title="Provincial UMR Gap vs National Average by Year",
            hover_data={
                "REGION": True,
                "GAP": ":,.0f",
                "SALARY": ":,.0f",
                "SALARY_NATIONAL": ":,.0f",
                "STATUS": True
            }
        )

    fig_gap.add_hline(y=0, line_dash="dash", line_color="gray")

    fig_gap.update_layout(
        xaxis_title=None,
        yaxis_title="UMR Gap (Rp)",
        legend_title="Province",
        margin=dict(t=60, b=40),
        height=500
    )

    st.plotly_chart(fig_gap, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# TOP & BOTTOM GAP UMR PROVINSI vs NASIONAL
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Top & Bottom {top_bottom_n} Provincial UMR Gap vs National Average ({year_from}–{year_to})")

df_gap_filtered = df_gap[(df_gap["YEAR"] >= year_from) & (df_gap["YEAR"] <= year_to)]
if df_gap_filtered.empty:
    st.warning("No data to calculate Top/Bottom Gap")
else:
    top_gap = df_gap_filtered.nlargest(top_bottom_n, "GAP")[["REGION", "YEAR", "GAP", "SALARY", "SALARY_NATIONAL"]].reset_index(drop=True)
    bot_gap = df_gap_filtered.nsmallest(top_bottom_n, "GAP")[["REGION", "YEAR", "GAP", "SALARY", "SALARY_NATIONAL"]].reset_index(drop=True)

    top_gap["LABEL"] = top_gap.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)
    bot_gap["LABEL"] = bot_gap.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)

    col_top_gap, col_bot_gap = st.columns(2)

    with col_top_gap:
        st.markdown(f"#### Top {top_bottom_n} Highest Gaps vs National Average")
        st.dataframe(
            top_gap.assign(
                GAP=lambda x: x["GAP"].apply(lambda y: f"Rp {int(y):,}"),
                SALARY=lambda x: x["SALARY"].apply(lambda y: f"Rp {int(y):,}"),
                SALARY_NATIONAL=lambda x: x["SALARY_NATIONAL"].apply(lambda y: f"Rp {int(y):,}")
            ).style.hide(axis="index"),
            use_container_width=True
        )

        order_top = top_gap.sort_values("GAP", ascending=True)["LABEL"].tolist()
        fig_top_gap = px.bar(
            top_gap,
            x="GAP",
            y="LABEL",
            orientation="h",
            text=top_gap["GAP"].apply(lambda y: f"Rp {int(y):,}"),
            color="GAP",
            color_continuous_scale="Viridis",
            category_orders={"LABEL": order_top},
            labels={"GAP": "Gap (Rp)", "LABEL": "Province (Year)"},
            title=f"Top {top_bottom_n} Highest Gaps vs National Average"
        )
        fig_top_gap.update_traces(hovertemplate="Province (Year): %{y}<br>Gap: Rp %{x:,.0f}<extra></extra>",textposition="inside", textfont=dict(color="white"))
        fig_top_gap.update_layout(showlegend=False, xaxis_title="Gap (Rp)", yaxis_title=None)
        st.plotly_chart(fig_top_gap, use_container_width=True)

    with col_bot_gap:
        st.markdown(f"#### Bottom {top_bottom_n} Lowest Gaps vs National Average")
        st.dataframe(
            bot_gap.assign(
                GAP=lambda x: x["GAP"].apply(lambda y: f"Rp {int(y):,}"),
                SALARY=lambda x: x["SALARY"].apply(lambda y: f"Rp {int(y):,}"),
                SALARY_NATIONAL=lambda x: x["SALARY_NATIONAL"].apply(lambda y: f"Rp {int(y):,}")
            ).style.hide(axis="index"),
            use_container_width=True
        )

        order_bot = bot_gap.sort_values("GAP", ascending=False)["LABEL"].tolist()
        fig_bot_gap = px.bar(
            bot_gap,
            x="GAP",
            y="LABEL",
            orientation="h",
            text=bot_gap["GAP"].apply(lambda y: f"Rp {int(y):,}"),
            color="GAP",
            color_continuous_scale="Reds",
            category_orders={"LABEL": order_bot},
            labels={"GAP": "Gap (Rp)", "LABEL": "Province (Year)"},
            title=f"Bottom {top_bottom_n} Lowest Gaps vs National Average"
        )
        fig_bot_gap.update_traces(hovertemplate="Province (Year): %{y}<br>Gap: Rp %{x:,.0f}<extra></extra>", textposition="inside", textfont=dict(color="white"))
        fig_bot_gap.update_layout(showlegend=False, xaxis_title="Gap (Rp)", yaxis_title=None)
        st.plotly_chart(fig_bot_gap, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# RASIO UMR PROVINSI terhadap NASIONAL (%)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Provincial UMR Ratio to National Average by Year ({year_from}–{year_to})")

df_ratio = df_year[df_year["REGION"].isin(selected_prov)].copy()
df_national_avg = df_year[df_year["REGION"].str.upper() == "INDONESIA"].copy()

if df_ratio.empty or df_national_avg.empty:
    st.info("No data to calculate Top/Bottom Ratio")
else:
    df_ratio = df_ratio.merge(
        df_national_avg[["YEAR", "SALARY"]],
        on="YEAR",
        how="left",
        suffixes=("", "_NATIONAL")
    )

    df_ratio["RATIO"] = (df_ratio["SALARY"] / df_ratio["SALARY_NATIONAL"]) * 100

    df_ratio["STATUS"] = df_ratio["RATIO"].apply(
        lambda x: "Above National Average" if x > 100 else ("Equal to National Average" if x == 100 else "Below National Average")
    )

    if year_from == year_to:
        fig_ratio = px.bar(
            df_ratio,
            x="REGION",
            y="RATIO",
            color="REGION",
            labels={
                "RATIO": "Ratio to National (%)",
                "REGION": "Province",
                "SALARY": "Provincial UMR",
                "SALARY_NATIONAL": "National UMR"
            },
            title=f"Provincial UMR Ratio to National Average by Year {year_from}",
            hover_data={
                "RATIO": ":.1f",
                "SALARY": ":,.0f",
                "SALARY_NATIONAL": ":,.0f",
                "STATUS": True
            }
        )
    else:
        fig_ratio = px.bar(
            df_ratio,
            x="YEAR",
            y="RATIO",
            color="REGION",
            barmode="group",
            labels={
                "RATIO": "Ratio to National (%)",
                "YEAR": "Year",
                "REGION": "Province",
                "SALARY": "Provincial UMR",
                "SALARY_NATIONAL": "National UMR"
            },
            title="Ratio Provincial UMR to National Average by Year",
            hover_data={
                "RATIO": ":.1f",
                "SALARY": ":,.0f",
                "SALARY_NATIONAL": ":,.0f",
                "STATUS": True
            }
        )

    fig_ratio.add_hline(y=100, line_dash="dash", line_color="gray")

    fig_ratio.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Ratio: %{y:.1f}%<br>"
            "Provincial UMR: Rp %{customdata[0]:,.0f}<br>"
            "National UMR: Rp %{customdata[1]:,.0f}<br>"
            "Status: %{customdata[2]}"
        ),
        customdata=df_ratio[["SALARY", "SALARY_NATIONAL", "STATUS"]],
        hoverlabel=dict(namelength=0)
    )

    fig_ratio.update_layout(
        xaxis_title=None,
        yaxis_title="Ratio to National (%)",
        legend_title="Province",
        margin=dict(t=60, b=40),
        height=500
    )

    st.plotly_chart(fig_ratio, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# TOP & BOTTOM RASIO UMR PROVINSI vs NASIONAL
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f"### Top & Bottom {top_bottom_n} Provincial UMR Ratios vs National Average ({year_from}–{year_to})")

df_ratio_filtered = df_ratio[(df_ratio["YEAR"] >= year_from) & (df_ratio["YEAR"] <= year_to)]
if df_ratio_filtered.empty:
    st.warning("No data to calculate Top/Bottom Ratio")
else:
    top_ratio = df_ratio_filtered.nlargest(top_bottom_n, "RATIO")[["REGION", "YEAR", "RATIO", "SALARY", "SALARY_NATIONAL"]].reset_index(drop=True)
    bot_ratio = df_ratio_filtered.nsmallest(top_bottom_n, "RATIO")[["REGION", "YEAR", "RATIO", "SALARY", "SALARY_NATIONAL"]].reset_index(drop=True)

    top_ratio["LABEL"] = top_ratio.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)
    bot_ratio["LABEL"] = bot_ratio.apply(lambda x: f"{x['REGION']} ({int(x['YEAR'])})", axis=1)


col_top_ratio, col_bot_ratio = st.columns(2, gap="large")
with col_top_ratio:
    with st.container():
        st.markdown(f"#### Top {top_bottom_n} Highest Ratios vs National Average")
        st.dataframe(
            top_ratio.assign(
                RATIO=lambda x: x["RATIO"].round(1).astype(str).str.replace('.', ',') + "%",
                SALARY=lambda x: x["SALARY"].apply(lambda y: f"Rp {int(y):,}"),
                SALARY_NATIONAL=lambda x: x["SALARY_NATIONAL"].apply(lambda y: f"Rp {int(y):,}")
            ).style.hide(axis="index"),
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        order_top_ratio = top_ratio.sort_values("RATIO", ascending=True)["LABEL"].tolist()
        fig_top_ratio = px.bar(
            top_ratio,
            x="RATIO",
            y="LABEL",
            orientation="h",
            text=top_ratio["RATIO"].round(1).astype(str).str.replace('.', ',') + "%",
            color="RATIO",
            color_continuous_scale="Viridis",
            category_orders={"LABEL": order_top_ratio},
            labels={"RATIO": "Ratio (%)", "LABEL": "Province (Year)"},
            title=f"Top {top_bottom_n} Highest Ratios vs National Average"
        )

        fig_top_ratio.update_traces(
            hovertemplate="Province (Year): %{y}<br>Ratio: %{x:.1f}%<extra></extra>",
            textposition="inside",
            textfont=dict(color="white", size=12)
        )
        fig_top_ratio.update_layout(
            showlegend=False,
            xaxis_title="Ratio (%)",
            yaxis_title=None,
            height=400
        )
        st.plotly_chart(fig_top_ratio, use_container_width=True)

with col_bot_ratio:
    with st.container():
        st.markdown(f"#### Bottom {top_bottom_n} Lowest Ratios vs National Average")
        st.dataframe(
            bot_ratio.assign(
                RATIO=lambda x: x["RATIO"].round(1).astype(str).str.replace('.', ',') + "%",
                SALARY=lambda x: x["SALARY"].apply(lambda y: f"Rp {int(y):,}"),
                SALARY_NATIONAL=lambda x: x["SALARY_NATIONAL"].apply(lambda y: f"Rp {int(y):,}")
            ).style.hide(axis="index"),
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        order_bot_ratio = bot_ratio.sort_values("RATIO", ascending=False)["LABEL"].tolist()
        fig_bot_ratio = px.bar(
            bot_ratio,
            x="RATIO",
            y="LABEL",
            orientation="h",
            text=bot_ratio["RATIO"].round(1).astype(str).str.replace('.', ',') + "%",
            color="RATIO",
            color_continuous_scale="Reds",
            category_orders={"LABEL": order_bot_ratio},
            labels={"RATIO": "Ratio (%)", "LABEL": "Province (Year)"},
            title=f"Bottom {top_bottom_n} Lowest Ratios vs National Average"
        )

        fig_bot_ratio.update_traces(
            hovertemplate="Province (Year): %{y}<br>Ratio: %{x:.1f}%<extra></extra>",
            textposition="inside",
            textfont=dict(color="white", size=12)
        )
        fig_bot_ratio.update_layout(
            showlegend=False,
            xaxis_title="Ratio (%)",
            yaxis_title=None,
            height=400
        )
        st.plotly_chart(fig_bot_ratio, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)


# FOOTER
st.markdown(
    "**Indonesia Minimum Wage Dashboard** · by [Fariz Sidki](https://www.linkedin.com/in/fariz-sidki/) · © 2025",
    unsafe_allow_html=True
)
