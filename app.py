import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Inbound Traffic Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Inbound Website Traffic Dashboard")
st.caption("Single-page MVP with column-level filters and a filtered session table.")

DEFAULT_FILE = "bq-results-20260609-135014-1781013034663.csv"

@st.cache_data(show_spinner=False)
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_csv(DEFAULT_FILE)

    # Parse timestamps when available
    for col in ["session_start_ts", "session_end_ts"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    # Useful derived fields for display and filtering
    if "session_start_ts" in df.columns:
        df["session_date"] = df["session_start_ts"].dt.date

    if {"session_start_ts", "session_end_ts"}.issubset(df.columns):
        df["session_duration_sec"] = (
            df["session_end_ts"] - df["session_start_ts"]
        ).dt.total_seconds().round(0)

    if "page_sequence" in df.columns:
        pages = df["page_sequence"].fillna("").astype(str).str.split(" > ")
        df["landing_page"] = pages.str[0].replace("", pd.NA)
        df["page_count"] = pages.apply(lambda x: len([p for p in x if p]))

    return df

uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

try:
    df = load_data(uploaded_file)
except FileNotFoundError:
    st.error(
        f"Could not find `{DEFAULT_FILE}`. Upload the CSV using the sidebar, "
        "or place the CSV in the same folder as this app."
    )
    st.stop()

filtered_df = df.copy()

st.subheader("Filters")

# Main date filter first
if "session_date" in filtered_df.columns and filtered_df["session_date"].notna().any():
    min_date = filtered_df["session_date"].min()
    max_date = filtered_df["session_date"].max()
    selected_range = st.date_input(
        "Session date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
        filtered_df = filtered_df[
            (filtered_df["session_date"] >= start_date)
            & (filtered_df["session_date"] <= end_date)
        ]

# Column-level filters
filter_columns = [
    "landing_type",
    "session_medium",
    "session_source",
    "geo_country",
    "geo_region",
    "geo_city",
    "landing_page",
]
filter_columns = [col for col in filter_columns if col in filtered_df.columns]

cols_per_row = 3
for i in range(0, len(filter_columns), cols_per_row):
    cols = st.columns(cols_per_row)
    for col_name, ui_col in zip(filter_columns[i : i + cols_per_row], cols):
        with ui_col:
            options = (
                filtered_df[col_name]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )
            selected = st.multiselect(
                label=col_name.replace("_", " ").title(),
                options=options,
                placeholder=f"All {col_name}",
            )
            if selected:
                filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected)]

# Text search across journey/events/source fields
search_text = st.text_input(
    "Search across page sequence, events, source, city, region, country",
    placeholder="Example: pricing, google, electronics, United States",
)
if search_text:
    searchable_cols = [
        col
        for col in [
            "page_sequence",
            "unique_events",
            "session_source",
            "session_medium",
            "landing_type",
            "geo_country",
            "geo_region",
            "geo_city",
        ]
        if col in filtered_df.columns
    ]
    mask = pd.Series(False, index=filtered_df.index)
    for col in searchable_cols:
        mask = mask | filtered_df[col].fillna("").astype(str).str.contains(
            search_text, case=False, na=False
        )
    filtered_df = filtered_df[mask]

st.divider()

# Summary cards
metric_cols = st.columns(4)
metric_cols[0].metric("Filtered sessions", f"{len(filtered_df):,}")
metric_cols[1].metric("Total sessions", f"{len(df):,}")

if "page_count" in filtered_df.columns and len(filtered_df) > 0:
    metric_cols[2].metric("Avg pages/session", f"{filtered_df['page_count'].mean():.2f}")
else:
    metric_cols[2].metric("Avg pages/session", "—")

if "session_duration_sec" in filtered_df.columns and len(filtered_df) > 0:
    metric_cols[3].metric(
        "Avg duration sec",
        f"{filtered_df['session_duration_sec'].dropna().mean():.0f}",
    )
else:
    metric_cols[3].metric("Avg duration sec", "—")

st.subheader("Session table")

# Choose visible columns, keeping raw columns plus useful derived fields
preferred_cols = [
    "session_start_ts",
    "session_end_ts",
    "session_duration_sec",
    "landing_type",
    "session_source",
    "session_medium",
    "geo_country",
    "geo_region",
    "geo_city",
    "landing_page",
    "page_count",
    "page_sequence",
    "unique_events",
    "session_key",
    "user_id",
    "anon_id",
]
visible_cols = [col for col in preferred_cols if col in filtered_df.columns]
remaining_cols = [col for col in filtered_df.columns if col not in visible_cols]
visible_cols = visible_cols + remaining_cols

st.dataframe(
    filtered_df[visible_cols],
    use_container_width=True,
    hide_index=True,
    height=650,
)

csv = filtered_df[visible_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download filtered CSV",
    data=csv,
    file_name="filtered_inbound_traffic.csv",
    mime="text/csv",
)
