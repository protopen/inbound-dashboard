from urllib.parse import urlparse

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Inbound Dashboard",
    page_icon="📊",
    layout="wide",
)

DEFAULT_FILE = "bq-results-20260609-135014-1781013034663.csv"
BLOG_PATH_PREFIXES = ("/blog", "/blogs")


@st.cache_data(show_spinner=False)
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_csv(DEFAULT_FILE)

    for col in ["session_start_ts", "session_end_ts"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    if "session_start_ts" in df.columns:
        df["session_date"] = df["session_start_ts"].dt.date

    if {"session_start_ts", "session_end_ts"}.issubset(df.columns):
        df["session_duration_sec"] = (
            df["session_end_ts"] - df["session_start_ts"]
        ).dt.total_seconds().round(0)

    if "page_sequence" in df.columns:
        df["pages"] = df["page_sequence"].apply(split_pages)
        df["path_sequence"] = df["pages"].apply(lambda pages: " > ".join(pages))
        df["landing_page"] = df["pages"].apply(lambda pages: pages[0] if pages else pd.NA)
        df["exit_page"] = df["pages"].apply(lambda pages: pages[-1] if pages else pd.NA)
        df["page_count"] = df["pages"].apply(len)
        df["reached_pricing"] = df["pages"].apply(lambda pages: any("/pricing" in p for p in pages))
        df["has_blog_visit"] = df["pages"].apply(lambda pages: any(is_blog_path(p) for p in pages))
        df["blog_landing_page"] = df["landing_page"].apply(
            lambda p: p if isinstance(p, str) and is_blog_path(p) else pd.NA
        )

    if "unique_events" in df.columns:
        df["has_user_engagement"] = df["unique_events"].fillna("").astype(str).str.contains(
            "user_engagement", case=False, na=False
        )

    return df


def normalize_path(value):
    if pd.isna(value):
        return ""
    value = str(value).strip()
    if not value or value.lower() == "nan":
        return ""

    parsed = urlparse(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value.split("?")[0]
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def split_pages(sequence):
    if pd.isna(sequence):
        return []
    return [normalize_path(p) for p in str(sequence).split(" > ") if normalize_path(p)]


def is_blog_path(path):
    if not isinstance(path, str):
        return False
    normalized = normalize_path(path).lower()
    return normalized == "/blogs" or normalized.startswith("/blog/")


def first_value(series):
    series = series.dropna()
    return series.iloc[0] if len(series) else pd.NA


def top_value(series):
    series = series.dropna().astype(str)
    if len(series) == 0:
        return "—"
    return series.value_counts().idxmax()


def blog_page_records(df):
    records = []
    if "pages" not in df.columns:
        return pd.DataFrame()

    for _, row in df.iterrows():
        pages = row.get("pages", []) or []
        if not pages:
            continue
        blog_positions = [idx for idx, path in enumerate(pages) if is_blog_path(path)]
        for idx in blog_positions:
            path = pages[idx]
            next_page = pages[idx + 1] if idx + 1 < len(pages) else pd.NA
            previous_page = pages[idx - 1] if idx > 0 else pd.NA
            reached_pricing_after = any("/pricing" in p for p in pages[idx + 1 :])
            records.append(
                {
                    "session_key": row.get("session_key"),
                    "session_date": row.get("session_date"),
                    "session_start_ts": row.get("session_start_ts"),
                    "session_duration_sec": row.get("session_duration_sec"),
                    "blog_path": path,
                    "blog_title_guess": path_to_title(path),
                    "position_in_journey": idx + 1,
                    "is_landing_page": idx == 0,
                    "is_exit_page": idx == len(pages) - 1,
                    "next_page": next_page,
                    "previous_page": previous_page,
                    "reached_pricing_after_blog": reached_pricing_after,
                    "page_count": row.get("page_count"),
                    "session_source": row.get("session_source"),
                    "session_medium": row.get("session_medium"),
                    "landing_type": row.get("landing_type"),
                    "geo_country": row.get("geo_country"),
                    "geo_region": row.get("geo_region"),
                    "geo_city": row.get("geo_city"),
                }
            )
    return pd.DataFrame(records)


def path_to_title(path):
    path = normalize_path(path)
    if path == "/blogs":
        return "Blogs index"
    slug = path.split("/")[-1]
    return slug.replace("-", " ").title() if slug else path


def pct(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return 0.0
    return 100 * numerator / denominator


def apply_global_filters(df):
    filtered_df = df.copy()

    st.markdown(
        """
        <style>
            div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] {
                gap: 0.35rem;
            }
            div[data-testid="stPopover"] button {
                width: 100%;
                min-height: 2.35rem;
            }
            .filter-summary {
                font-size: 0.85rem;
                color: #666;
                margin-top: -0.35rem;
                margin-bottom: 0.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Filters")
    st.caption("Compact filter bar. Open any filter button to refine; selected filters stay active.")

    date_col, search_col, count_col = st.columns([1.25, 2.6, 0.8])

    with date_col:
        if "session_date" in filtered_df.columns and filtered_df["session_date"].notna().any():
            min_date = filtered_df["session_date"].min()
            max_date = filtered_df["session_date"].max()
            selected_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                label_visibility="collapsed",
            )
            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                start_date, end_date = selected_range
                filtered_df = filtered_df[
                    (filtered_df["session_date"] >= start_date)
                    & (filtered_df["session_date"] <= end_date)
                ]

    with search_col:
        search_text = st.text_input(
            "Search",
            placeholder="Search journey, events, source, geo...",
            label_visibility="collapsed",
        )

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

    selected_filters = {}
    compact_cols = st.columns(len(filter_columns) if filter_columns else 1)
    for col_name, ui_col in zip(filter_columns, compact_cols):
        label = col_name.replace("_", " ").title()
        with ui_col:
            options = (
                filtered_df[col_name]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )
            if hasattr(st, "popover"):
                with st.popover(label):
                    selected = st.multiselect(
                        label,
                        options=options,
                        placeholder=f"All {label.lower()}",
                        key=f"filter_{col_name}",
                    )
            else:
                # Fallback for older Streamlit versions.
                with st.expander(label, expanded=False):
                    selected = st.multiselect(
                        label,
                        options=options,
                        placeholder=f"All {label.lower()}",
                        key=f"filter_{col_name}",
                    )
            selected_filters[col_name] = selected

    active_filter_labels = []
    for col_name, selected in selected_filters.items():
        if selected:
            filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected)]
            active_filter_labels.append(
                f"{col_name.replace('_', ' ').title()}: {len(selected)}"
            )

    if search_text:
        searchable_cols = [
            col
            for col in [
                "page_sequence",
                "path_sequence",
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
        active_filter_labels.append("Search")

    with count_col:
        st.metric("Rows", f"{len(filtered_df):,}")

    if active_filter_labels:
        st.markdown(
            f'<div class="filter-summary">Active: {" | ".join(active_filter_labels)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="filter-summary">Active: none</div>', unsafe_allow_html=True)

    return filtered_df


def render_overview_table(filtered_df, df):
    st.divider()

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
        "exit_page",
        "page_count",
        "reached_pricing",
        "has_blog_visit",
        "path_sequence",
        "page_sequence",
        "unique_events",
        "session_key",
        "user_id",
        "anon_id",
    ]
    visible_cols = [col for col in preferred_cols if col in filtered_df.columns]
    remaining_cols = [col for col in filtered_df.columns if col not in visible_cols and col != "pages"]
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


def render_blogs_page(filtered_df):
    st.divider()
    st.subheader("Blog page analysis")
    st.caption(
        "Analyzes all sessions whose journey includes `/blog/...` pages or the `/blogs` index. "
        "Unique sessions are counted by blog path, so repeated views inside the same session are not double-counted."
    )

    blog_records = blog_page_records(filtered_df)
    if blog_records.empty:
        st.info("No blog page visits found for the current filters.")
        return

    unique_blog_sessions = blog_records["session_key"].nunique()
    total_blog_pageviews = len(blog_records)
    unique_blog_paths = blog_records["blog_path"].nunique()
    blog_landing_sessions = blog_records.loc[blog_records["is_landing_page"], "session_key"].nunique()
    pricing_after_sessions = blog_records.loc[
        blog_records["reached_pricing_after_blog"], "session_key"
    ].nunique()

    metric_cols = st.columns(5)
    metric_cols[0].metric("Blog sessions", f"{unique_blog_sessions:,}")
    metric_cols[1].metric("Unique blog paths", f"{unique_blog_paths:,}")
    metric_cols[2].metric("Blog pageviews", f"{total_blog_pageviews:,}")
    metric_cols[3].metric("Blog landing sessions", f"{blog_landing_sessions:,}")
    metric_cols[4].metric(
        "Reached pricing after blog",
        f"{pricing_after_sessions:,}",
        f"{pct(pricing_after_sessions, unique_blog_sessions):.1f}%",
    )

    by_blog = (
        blog_records.groupby(["blog_path", "blog_title_guess"], dropna=False)
        .agg(
            unique_sessions=("session_key", "nunique"),
            blog_pageviews=("session_key", "size"),
            landing_sessions=("is_landing_page", "sum"),
            exit_sessions=("is_exit_page", "sum"),
            pricing_after_blog_sessions=(
                "reached_pricing_after_blog",
                lambda s: blog_records.loc[s.index[s], "session_key"].nunique(),
            ),
            avg_position_in_journey=("position_in_journey", "mean"),
            avg_pages_per_session=("page_count", "mean"),
            avg_duration_sec=("session_duration_sec", "mean"),
            top_source=("session_source", top_value),
            top_medium=("session_medium", top_value),
            top_country=("geo_country", top_value),
            top_next_page=("next_page", top_value),
        )
        .reset_index()
    )

    by_blog["landing_rate"] = by_blog.apply(
        lambda r: pct(r["landing_sessions"], r["unique_sessions"]), axis=1
    )
    by_blog["exit_rate"] = by_blog.apply(
        lambda r: pct(r["exit_sessions"], r["unique_sessions"]), axis=1
    )
    by_blog["pricing_after_rate"] = by_blog.apply(
        lambda r: pct(r["pricing_after_blog_sessions"], r["unique_sessions"]), axis=1
    )

    by_blog = by_blog.sort_values(["unique_sessions", "blog_pageviews"], ascending=False)

    st.markdown("### Top blog paths by unique sessions")
    chart_data = by_blog.head(15).set_index("blog_path")[["unique_sessions"]]
    st.bar_chart(chart_data)

    st.markdown("### Blog path performance table")
    display_cols = [
        "blog_path",
        "blog_title_guess",
        "unique_sessions",
        "blog_pageviews",
        "landing_sessions",
        "landing_rate",
        "exit_sessions",
        "exit_rate",
        "pricing_after_blog_sessions",
        "pricing_after_rate",
        "avg_position_in_journey",
        "avg_pages_per_session",
        "avg_duration_sec",
        "top_source",
        "top_medium",
        "top_country",
        "top_next_page",
    ]
    st.dataframe(
        by_blog[display_cols],
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "landing_rate": st.column_config.NumberColumn("Landing rate", format="%.1f%%"),
            "exit_rate": st.column_config.NumberColumn("Exit rate", format="%.1f%%"),
            "pricing_after_rate": st.column_config.NumberColumn("Pricing after rate", format="%.1f%%"),
            "avg_position_in_journey": st.column_config.NumberColumn("Avg journey position", format="%.2f"),
            "avg_pages_per_session": st.column_config.NumberColumn("Avg pages/session", format="%.2f"),
            "avg_duration_sec": st.column_config.NumberColumn("Avg duration sec", format="%.0f"),
        },
    )

    st.markdown("### Blog traffic source mix")
    source_mix = (
        blog_records.groupby(["session_source", "session_medium"], dropna=False)["session_key"]
        .nunique()
        .reset_index(name="unique_sessions")
        .sort_values("unique_sessions", ascending=False)
        .head(25)
    )
    st.dataframe(source_mix, use_container_width=True, hide_index=True)

    st.markdown("### Blog next-page behavior")
    next_pages = (
        blog_records.dropna(subset=["next_page"])
        .groupby("next_page")["session_key"]
        .nunique()
        .reset_index(name="unique_sessions")
        .sort_values("unique_sessions", ascending=False)
        .head(25)
    )
    if next_pages.empty:
        st.info("No next-page movement found after blog pages in the current filters.")
    else:
        st.dataframe(next_pages, use_container_width=True, hide_index=True)

    st.markdown("### Blog SEO opportunity flags")
    opportunity = by_blog.copy()
    opportunity["opportunity_note"] = ""
    opportunity.loc[
        (opportunity["unique_sessions"] >= 3) & (opportunity["exit_rate"] >= 70),
        "opportunity_note",
    ] = "High blog traffic but high exit rate. Add stronger internal links or CTAs."
    opportunity.loc[
        (opportunity["unique_sessions"] >= 3) & (opportunity["pricing_after_rate"] >= 20),
        "opportunity_note",
    ] = "This blog appears to send readers toward pricing. Consider using it as a commercial SEO asset."
    opportunity.loc[
        (opportunity["landing_sessions"] >= 3) & (opportunity["landing_rate"] >= 60),
        "opportunity_note",
    ] = "This is often the first page in the session. Make the above-the-fold path clear."
    opportunity = opportunity[opportunity["opportunity_note"] != ""]

    if opportunity.empty:
        st.info("No automatic blog opportunity flags for the current filters yet.")
    else:
        st.dataframe(
            opportunity[
                [
                    "blog_path",
                    "unique_sessions",
                    "landing_rate",
                    "exit_rate",
                    "pricing_after_rate",
                    "top_source",
                    "top_next_page",
                    "opportunity_note",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "landing_rate": st.column_config.NumberColumn("Landing rate", format="%.1f%%"),
                "exit_rate": st.column_config.NumberColumn("Exit rate", format="%.1f%%"),
                "pricing_after_rate": st.column_config.NumberColumn("Pricing after rate", format="%.1f%%"),
            },
        )

    csv = by_blog[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download blog path analysis CSV",
        data=csv,
        file_name="blog_path_analysis.csv",
        mime="text/csv",
    )


st.title("Inbound Dashboard")
st.caption("Website traffic, journeys, sources, and blog performance analysis.")

uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

try:
    df = load_data(uploaded_file)
except FileNotFoundError:
    st.error(
        f"Could not find `{DEFAULT_FILE}`. Upload the CSV using the sidebar, "
        "or place the CSV in the same folder as this app."
    )
    st.stop()

filtered_df = apply_global_filters(df)

tab_sessions, tab_blogs = st.tabs(["Session table", "Blogs"])

with tab_sessions:
    render_overview_table(filtered_df, df)

with tab_blogs:
    render_blogs_page(filtered_df)
