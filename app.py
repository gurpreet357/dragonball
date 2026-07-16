"""
Cultivating Insight — Crop Production Analytics Dashboard
Streamlit app for exploring the crop_production.csv dataset.

Run with:
    streamlit run app.py

Expects crop_production.csv in the same folder as this script
(columns: State_Name, Crop_Type, Crop, N, P, K, pH, rainfall,
temperature, Area_in_hectares, Production_in_tons, Yield_ton_per_hec).

Only dependencies: streamlit, pandas, numpy, plotly.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------
st.set_page_config(
    page_title="Crop Production Analytics",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

FOREST = "#2C5F2D"
MOSS = "#6B8E4E"
MOSS_LIGHT = "#97BC62"
GOLD = "#D9A441"
PALETTE = [FOREST, MOSS, GOLD, MOSS_LIGHT, "#8C6D3F", "#4C7A3D"]

NUMERIC_COLS = ["N", "P", "K", "pH", "rainfall", "temperature",
                 "Area_in_hectares", "Production_in_tons", "Yield_ton_per_hec"]

REQUIRED_COLS = {"State_Name", "Crop_Type", "Crop", "N", "P", "K", "pH", "rainfall",
                  "temperature", "Area_in_hectares", "Production_in_tons", "Yield_ton_per_hec"}

st.markdown(
    """
    <style>
    .stMetric { background-color: #F4F6EE; border-radius: 10px; padding: 12px; }
    div[data-testid="stMetricValue"] { color: #2C5F2D; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------
@st.cache_data
def load_data(path: str = "crop_production.csv") -> pd.DataFrame:
    data = pd.read_csv(path)
    if "Unnamed: 0" in data.columns:
        data = data.drop(columns=["Unnamed: 0"])

    missing = REQUIRED_COLS - set(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required column(s): {sorted(missing)}")

    data["State_Name"] = data["State_Name"].astype(str).str.strip().str.lower()
    data["Crop_Type"] = data["Crop_Type"].astype(str).str.strip().str.lower()
    data["Crop"] = data["Crop"].astype(str).str.strip().str.lower()

    for col in NUMERIC_COLS:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=NUMERIC_COLS)

    return data

st.title("🌾 Cultivating Insight")
st.caption("A Data-Driven Analysis of Crop Production Across India")

try:
    df = load_data()
except FileNotFoundError:
    st.error(
        "Couldn't find **crop_production.csv**. Place it in the same folder as "
        "this script (or edit the `path` argument in `load_data()`), then rerun."
    )
    st.stop()
except ValueError as e:
    st.error(f"Dataset format problem: {e}")
    st.stop()
except Exception as e:  # noqa: BLE001 — surface any other loading issue clearly
    st.error(f"Couldn't load the dataset: {e}")
    st.stop()

if df.empty:
    st.error("The dataset loaded but contains no usable rows after cleaning.")
    st.stop()

# -----------------------------------------------------------------
# SIDEBAR — FILTERS
# -----------------------------------------------------------------
st.sidebar.title("🌾 Filters")

states_all = sorted(df["State_Name"].unique())
crop_types_all = sorted(df["Crop_Type"].unique())

sel_states = st.sidebar.multiselect(
    "State", options=states_all, default=[],
    format_func=lambda x: x.title(),
    help="Leave empty to include all states.",
)
sel_crop_types = st.sidebar.multiselect(
    "Crop Season", options=crop_types_all, default=[],
    format_func=lambda x: x.title(),
    help="Leave empty to include all seasons.",
)

# Crop list depends on the crop-type filter so it stays relevant
crop_pool = df if not sel_crop_types else df[df["Crop_Type"].isin(sel_crop_types)]
crops_all = sorted(crop_pool["Crop"].unique())
sel_crops = st.sidebar.multiselect(
    "Crop", options=crops_all, default=[],
    format_func=lambda x: x.title(),
    help="Leave empty to include all crops.",
)

exclude_outliers = st.sidebar.checkbox(
    "Exclude yield outliers (> 30 t/ha)", value=True,
    help="A small number of records have implausible yields (max in the raw data "
         "can run into the thousands t/ha) that distort averages and chart scales.",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Dataset: **{len(df):,}** records · **{df['State_Name'].nunique()}** states · "
    f"**{df['Crop'].nunique()}** crops"
)

# -----------------------------------------------------------------
# APPLY FILTERS
# -----------------------------------------------------------------
filtered = df.copy()
if sel_states:
    filtered = filtered[filtered["State_Name"].isin(sel_states)]
if sel_crop_types:
    filtered = filtered[filtered["Crop_Type"].isin(sel_crop_types)]
if sel_crops:
    filtered = filtered[filtered["Crop"].isin(sel_crops)]
if exclude_outliers:
    filtered = filtered[filtered["Yield_ton_per_hec"] <= 30]

if filtered.empty:
    st.warning("No records match the current filters. Try widening your selection.")
    st.stop()

# -----------------------------------------------------------------
# KPIs
# -----------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Records", f"{len(filtered):,}")
k2.metric("Total Production", f"{filtered['Production_in_tons'].sum() / 1e6:,.1f}M tons")
k3.metric("Total Area", f"{filtered['Area_in_hectares'].sum() / 1e6:,.1f}M ha")
k4.metric("Avg. Yield", f"{filtered['Yield_ton_per_hec'].mean():.2f} t/ha")
k5.metric("States / Crops", f"{filtered['State_Name'].nunique()} / {filtered['Crop'].nunique()}")

st.markdown("---")

# -----------------------------------------------------------------
# TABS
# -----------------------------------------------------------------
tab_overview, tab_yield, tab_correlation, tab_explore = st.tabs(
    ["📊 Production Overview", "🌱 Yield Analysis", "🔗 Correlations", "🔍 Explore Data"]
)

# ============================ TAB 1: OVERVIEW ============================
with tab_overview:
    col1, col2 = st.columns(2)

    with col1:
        top_states = (
            filtered.groupby("State_Name")["Production_in_tons"].sum()
            .sort_values(ascending=False).head(10).reset_index()
        )
        top_states["State_Name"] = top_states["State_Name"].str.title()
        fig = px.bar(
            top_states, x="Production_in_tons", y="State_Name", orientation="h",
            color_discrete_sequence=[FOREST],
            labels={"Production_in_tons": "Production (tons)", "State_Name": "State"},
            title="Top 10 States by Total Production",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_crops = (
            filtered.groupby("Crop")["Production_in_tons"].sum()
            .sort_values(ascending=False).head(10).reset_index()
        )
        top_crops["Crop"] = top_crops["Crop"].str.title()
        fig = px.bar(
            top_crops, x="Production_in_tons", y="Crop", orientation="h",
            color_discrete_sequence=[GOLD],
            labels={"Production_in_tons": "Production (tons)", "Crop": "Crop"},
            title="Top 10 Crops by Total Production",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        share = (
            filtered.groupby("Crop_Type")["Production_in_tons"].sum()
            .sort_values(ascending=False).reset_index()
        )
        share["Crop_Type"] = share["Crop_Type"].str.title()
        fig = px.pie(
            share, names="Crop_Type", values="Production_in_tons", hole=0.4,
            color_discrete_sequence=PALETTE, title="Production Share by Crop Season",
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        top10_states_idx = (
            filtered.groupby("State_Name")["Production_in_tons"].sum()
            .sort_values(ascending=False).head(10).index
        )
        subset = filtered[filtered["State_Name"].isin(top10_states_idx)].copy()
        subset["State_Name"] = subset["State_Name"].str.title()
        subset["Crop"] = subset["Crop"].str.title()
        agg = subset.groupby(["State_Name", "Crop"])["Production_in_tons"].sum().reset_index()
        agg = agg.sort_values(["State_Name", "Production_in_tons"], ascending=[True, False])
        agg = agg.groupby("State_Name").head(5)

        if agg.empty:
            st.info("Not enough data for a treemap with the current filters.")
        else:
            fig = px.treemap(
                agg, path=["State_Name", "Crop"], values="Production_in_tons",
                color="Production_in_tons", color_continuous_scale="Greens",
                title="Production by State → Top 5 Crops (Top 10 States)",
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================ TAB 2: YIELD ============================
with tab_yield:
    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(
            filtered, x="Yield_ton_per_hec", nbins=60, color_discrete_sequence=[FOREST],
            marginal="box", title="Distribution of Crop Yield",
            labels={"Yield_ton_per_hec": "Yield (tons/hectare)"},
        )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.box(
            filtered, x="Yield_ton_per_hec", y="Crop_Type", color="Crop_Type",
            color_discrete_sequence=PALETTE, points=False,
            title="Yield Distribution by Crop Season",
            labels={"Yield_ton_per_hec": "Yield (tons/hectare)", "Crop_Type": "Season"},
        )
        fig.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        top_yield_crops = (
            filtered.groupby("Crop")["Yield_ton_per_hec"].mean()
            .sort_values(ascending=False).head(10).reset_index()
        )
        top_yield_crops["Crop"] = top_yield_crops["Crop"].str.title()
        fig = px.bar(
            top_yield_crops, x="Yield_ton_per_hec", y="Crop", orientation="h",
            color_discrete_sequence=[MOSS_LIGHT],
            labels={"Yield_ton_per_hec": "Average Yield (tons/hectare)", "Crop": "Crop"},
            title="Top 10 Crops by Average Yield",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        sample = filtered.sample(min(5000, len(filtered)), random_state=42).copy()
        sample["Crop_Type"] = sample["Crop_Type"].str.title()
        fig = px.scatter(
            sample, x="N", y="Yield_ton_per_hec", color="Crop_Type", opacity=0.5,
            color_discrete_sequence=PALETTE,
            labels={"N": "Nitrogen (N)", "Yield_ton_per_hec": "Yield (tons/hectare)"},
            title="Nitrogen vs. Yield by Crop Season",
        )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

# ============================ TAB 3: CORRELATIONS ============================
with tab_correlation:
    if len(filtered) < 5:
        st.info(
            "Not enough data points in the current filter to compute a meaningful "
            "correlation matrix. Try widening your filters.",
            icon="ℹ️",
        )
    else:
        corr = filtered[NUMERIC_COLS].corr()

        fig = px.imshow(
            corr, text_auto=".2f", color_continuous_scale="Greens", zmin=-1, zmax=1,
            title="Correlation Matrix — Numeric Features", aspect="auto",
        )
        fig.update_layout(template="plotly_white", height=550)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Area vs. Production")
        sample = filtered.sample(min(3000, len(filtered)), random_state=42)
        fig = px.scatter(
            sample, x="Area_in_hectares", y="Production_in_tons", opacity=0.4,
            color_discrete_sequence=[MOSS],
            labels={"Area_in_hectares": "Area (hectares)", "Production_in_tons": "Production (tons)"},
            title="Area vs. Production (3,000-row sample, with trend line)",
        )
        # Manual linear trend line via numpy — no statsmodels dependency required.
        if sample["Area_in_hectares"].nunique() > 1:
            coeffs = np.polyfit(sample["Area_in_hectares"], sample["Production_in_tons"], 1)
            x_range = np.linspace(sample["Area_in_hectares"].min(), sample["Area_in_hectares"].max(), 100)
            y_line = np.polyval(coeffs, x_range)
            fig.add_scatter(
                x=x_range, y=y_line, mode="lines", name="Linear trend",
                line=dict(color=GOLD, width=3),
            )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        st.info(
            "Cultivated area correlates strongly with total production, but individual soil "
            "nutrients and climate variables (N, rainfall, pH, temperature) show weak linear "
            "correlation with per-hectare yield — yield is likely driven by nonlinear, "
            "crop-specific interactions rather than any single input.",
            icon="💡",
        )

# ============================ TAB 4: EXPLORE ============================
with tab_explore:
    st.markdown(f"##### Filtered data — {len(filtered):,} rows")
    st.dataframe(filtered.reset_index(drop=True), use_container_width=True, height=420)

    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download filtered data as CSV", data=csv_bytes,
        file_name="filtered_crop_production.csv", mime="text/csv",
    )

    with st.expander("Summary statistics"):
        st.dataframe(filtered[NUMERIC_COLS].describe().T, use_container_width=True)