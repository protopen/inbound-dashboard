from urllib.parse import urlparse

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Inbound Dashboard",
    page_icon="📊",
    layout="wide",
)

DEFAULT_FILE = "bq-results-20260609-135014-1781013034663.csv"
BLOG_PATH_PREFIXES = ("/blog", "/blogs")
INTENT_PAGE_DEFINITIONS = {
    "pricing": {
        "label": "Pricing",
        "column": "reached_pricing",
        "after_blog_column": "reached_pricing_after_blog",
        "sessions_column": "pricing_after_blog_sessions",
        "rate_column": "pricing_after_rate",
    },
    "scheduledemo": {
        "label": "Schedule demo",
        "column": "reached_scheduledemo",
        "after_blog_column": "reached_scheduledemo_after_blog",
        "sessions_column": "scheduledemo_after_blog_sessions",
        "rate_column": "scheduledemo_after_rate",
    },
    "contactus": {
        "label": "Contact us",
        "column": "reached_contactus",
        "after_blog_column": "reached_contactus_after_blog",
        "sessions_column": "contactus_after_blog_sessions",
        "rate_column": "contactus_after_rate",
    },
}


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
        for intent_key, intent_meta in INTENT_PAGE_DEFINITIONS.items():
            df[intent_meta["column"]] = df["pages"].apply(
                lambda pages, key=intent_key: any(is_intent_page(p, key) for p in pages)
            )
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


def compact_path_token(path):
    return "".join(ch for ch in normalize_path(path).lower() if ch.isalnum())


def is_intent_page(path, intent_key):
    normalized = normalize_path(path).lower()
    compact = compact_path_token(path)

    if intent_key == "pricing":
        return "/pricing" in normalized or compact == "pricing"
    if intent_key == "scheduledemo":
        return "scheduledemo" in compact or "bookdemo" in compact or "requestdemo" in compact
    if intent_key == "contactus":
        return "contactus" in compact or compact == "contact" or compact.endswith("contact")
    return False


def reached_intent_after_page(pages, start_idx, intent_key):
    return any(is_intent_page(path, intent_key) for path in pages[start_idx + 1 :])


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
            reached_after_blog = {
                intent_meta["after_blog_column"]: reached_intent_after_page(pages, idx, intent_key)
                for intent_key, intent_meta in INTENT_PAGE_DEFINITIONS.items()
            }
            record = {
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
                    "page_count": row.get("page_count"),
                    "session_source": row.get("session_source"),
                    "session_medium": row.get("session_medium"),
                    "landing_type": row.get("landing_type"),
                    "geo_country": row.get("geo_country"),
                    "geo_region": row.get("geo_region"),
                    "geo_city": row.get("geo_city"),
                }
            record.update(reached_after_blog)
            records.append(record)
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


def display_path_label(path, max_chars=58):
    path = normalize_path(path)
    if len(path) <= max_chars:
        return path
    return path[: max_chars - 1] + "…"


def build_sankey_transitions(df, max_depth=5, top_pages_per_step=12, min_sessions=1, include_dropoffs=True):
    if "pages" not in df.columns or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    session_col = "session_key" if "session_key" in df.columns else None
    working = df[["pages"] + ([session_col] if session_col else [])].copy()
    if session_col is None:
        working["session_key"] = working.index.astype(str)
        session_col = "session_key"

    step_page_records = []
    session_paths = []

    for _, row in working.iterrows():
        session_key = row[session_col]
        pages = row.get("pages", []) or []
        pages = [normalize_path(p) for p in pages if normalize_path(p)]
        if not pages:
            continue

        capped_pages = pages[:max_depth]
        session_paths.append((session_key, pages, capped_pages))
        for step_idx, path in enumerate(capped_pages, start=1):
            step_page_records.append(
                {"step": step_idx, "page": path, "session_key": session_key}
            )

    if not step_page_records:
        return pd.DataFrame(), pd.DataFrame()

    step_pages = pd.DataFrame(step_page_records)
    top_pages = (
        step_pages.groupby(["step", "page"])["session_key"]
        .nunique()
        .reset_index(name="sessions")
        .sort_values(["step", "sessions"], ascending=[True, False])
        .groupby("step")
        .head(top_pages_per_step)
    )
    top_lookup = set(zip(top_pages["step"], top_pages["page"]))

    transition_records = []
    for session_key, pages, capped_pages in session_paths:
        if not capped_pages:
            continue

        mapped_pages = []
        for step_idx, path in enumerate(capped_pages, start=1):
            if (step_idx, path) in top_lookup:
                mapped_pages.append(path)
            else:
                mapped_pages.append(f"Other pages at step {step_idx}")

        for idx in range(len(mapped_pages) - 1):
            source_step = idx + 1
            target_step = idx + 2
            transition_records.append(
                {
                    "source_step": source_step,
                    "source_page": mapped_pages[idx],
                    "target_step": target_step,
                    "target_page": mapped_pages[idx + 1],
                    "session_key": session_key,
                    "transition_type": "Next page",
                }
            )

        last_observed_step = len(mapped_pages)
        if include_dropoffs:
            if len(pages) <= max_depth:
                transition_records.append(
                    {
                        "source_step": last_observed_step,
                        "source_page": mapped_pages[-1],
                        "target_step": last_observed_step + 1,
                        "target_page": f"Drop-off after step {last_observed_step}",
                        "session_key": session_key,
                        "transition_type": "Drop-off",
                    }
                )
            else:
                transition_records.append(
                    {
                        "source_step": last_observed_step,
                        "source_page": mapped_pages[-1],
                        "target_step": last_observed_step + 1,
                        "target_page": f"Continues beyond step {last_observed_step}",
                        "session_key": session_key,
                        "transition_type": "Continues",
                    }
                )

    if not transition_records:
        return pd.DataFrame(), pd.DataFrame()

    transitions = (
        pd.DataFrame(transition_records)
        .groupby(
            ["source_step", "source_page", "target_step", "target_page", "transition_type"],
            dropna=False,
        )["session_key"]
        .nunique()
        .reset_index(name="sessions")
    )
    transitions = transitions[transitions["sessions"] >= min_sessions]
    transitions = transitions.sort_values(
        ["source_step", "sessions"], ascending=[True, False]
    ).reset_index(drop=True)

    node_records = []
    for _, r in transitions.iterrows():
        node_records.append({"step": r["source_step"], "page": r["source_page"]})
        node_records.append({"step": r["target_step"], "page": r["target_page"]})
    nodes = pd.DataFrame(node_records).drop_duplicates().sort_values(["step", "page"])
    nodes["node_key"] = nodes.apply(lambda r: f"{int(r['step'])}|{r['page']}", axis=1)
    nodes["label"] = nodes.apply(
        lambda r: f"{int(r['step'])}. {display_path_label(r['page'])}"
        if not str(r["page"]).startswith(("Drop-off", "Continues"))
        else str(r["page"]),
        axis=1,
    )
    nodes["node_id"] = range(len(nodes))
    node_lookup = dict(zip(nodes["node_key"], nodes["node_id"]))

    transitions["source_key"] = transitions.apply(
        lambda r: f"{int(r['source_step'])}|{r['source_page']}", axis=1
    )
    transitions["target_key"] = transitions.apply(
        lambda r: f"{int(r['target_step'])}|{r['target_page']}", axis=1
    )
    transitions["source_id"] = transitions["source_key"].map(node_lookup)
    transitions["target_id"] = transitions["target_key"].map(node_lookup)
    transitions["source_label"] = transitions["source_key"].map(dict(zip(nodes["node_key"], nodes["label"])))
    transitions["target_label"] = transitions["target_key"].map(dict(zip(nodes["node_key"], nodes["label"])))

    return transitions, nodes


def render_journey_sankey_page(filtered_df):
    st.divider()
    st.subheader("Journey Sankey")
    st.caption("Visualizes page-to-page movement from `page_sequence`. Drop-off nodes show where sessions end within the selected journey depth.")

    if "pages" not in filtered_df.columns or filtered_df.empty:
        st.info("No journey data found for the current filters.")
        return

    control_cols = st.columns([1, 1, 1, 1.2])
    with control_cols[0]:
        max_depth = st.slider("Journey depth", min_value=2, max_value=8, value=5)
    with control_cols[1]:
        top_pages_per_step = st.slider("Top pages / step", min_value=5, max_value=30, value=12)
    with control_cols[2]:
        min_sessions = st.number_input("Min sessions / link", min_value=1, max_value=1000, value=1, step=1)
    with control_cols[3]:
        include_dropoffs = st.toggle("Show drop-offs", value=True)

    transitions, nodes = build_sankey_transitions(
        filtered_df,
        max_depth=max_depth,
        top_pages_per_step=top_pages_per_step,
        min_sessions=min_sessions,
        include_dropoffs=include_dropoffs,
    )

    if transitions.empty or nodes.empty:
        st.info("No Sankey transitions match the current filters and thresholds.")
        return

    total_sessions = len(filtered_df)
    single_page_sessions = int((filtered_df.get("page_count", pd.Series(dtype=int)) <= 1).sum()) if "page_count" in filtered_df.columns else 0
    avg_depth = filtered_df["page_count"].mean() if "page_count" in filtered_df.columns else 0
    observed_links = int(len(transitions))

    metric_cols = st.columns(4)
    metric_cols[0].metric("Sessions in view", f"{total_sessions:,}")
    metric_cols[1].metric("Avg journey depth", f"{avg_depth:.2f}" if total_sessions else "—")
    metric_cols[2].metric("Single-page sessions", f"{single_page_sessions:,}", f"{pct(single_page_sessions, total_sessions):.1f}%")
    metric_cols[3].metric("Displayed links", f"{observed_links:,}")

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=18,
                    thickness=16,
                    line=dict(width=0.4),
                    label=nodes["label"].tolist(),
                ),
                link=dict(
                    source=transitions["source_id"].astype(int).tolist(),
                    target=transitions["target_id"].astype(int).tolist(),
                    value=transitions["sessions"].astype(int).tolist(),
                    customdata=transitions["transition_type"].tolist(),
                    hovertemplate="%{source.label} → %{target.label}<br>Sessions: %{value}<br>%{customdata}<extra></extra>",
                ),
            )
        ]
    )
    fig.update_layout(
        height=720,
        margin=dict(l=10, r=10, t=20, b=10),
        font=dict(size=11),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Journey transition table")
    table = transitions[
        [
            "source_step",
            "source_page",
            "target_step",
            "target_page",
            "transition_type",
            "sessions",
        ]
    ].copy()
    table["share_of_filtered_sessions"] = table["sessions"].apply(lambda x: pct(x, total_sessions))
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "share_of_filtered_sessions": st.column_config.NumberColumn("Share of filtered sessions", format="%.1f%%"),
        },
    )

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download journey transition CSV",
        data=csv,
        file_name="journey_sankey_transitions.csv",
        mime="text/csv",
    )


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

    date_col, search_col = st.columns([1.25, 2.6])

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
                    default_options = [country for country in ["United States", "Canada"] if col_name == "geo_country" and country in options]
                    selected = st.multiselect(
                        label,
                        options=options,
                        default=default_options,
                        placeholder=f"All {label.lower()}",
                        key=f"filter_{col_name}",
                    )
            else:
                # Fallback for older Streamlit versions.
                with st.expander(label, expanded=False):
                    default_options = [country for country in ["United States", "Canada"] if col_name == "geo_country" and country in options]
                    selected = st.multiselect(
                        label,
                        options=options,
                        default=default_options,
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
        "reached_scheduledemo",
        "reached_contactus",
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
    intent_after_sessions = {
        intent_key: blog_records.loc[
            blog_records[intent_meta["after_blog_column"]], "session_key"
        ].nunique()
        for intent_key, intent_meta in INTENT_PAGE_DEFINITIONS.items()
    }

    metric_cols = st.columns(4)
    metric_cols[0].metric("Blog sessions", f"{unique_blog_sessions:,}")
    metric_cols[1].metric("Unique blog paths", f"{unique_blog_paths:,}")
    metric_cols[2].metric("Blog pageviews", f"{total_blog_pageviews:,}")
    metric_cols[3].metric("Blog landing sessions", f"{blog_landing_sessions:,}")

    intent_metric_cols = st.columns(3)
    for idx, (intent_key, intent_meta) in enumerate(INTENT_PAGE_DEFINITIONS.items()):
        sessions = intent_after_sessions[intent_key]
        intent_metric_cols[idx].metric(
            f"Reached {intent_meta['label'].lower()} after blog",
            f"{sessions:,}",
            f"{pct(sessions, unique_blog_sessions):.1f}%",
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
            scheduledemo_after_blog_sessions=(
                "reached_scheduledemo_after_blog",
                lambda s: blog_records.loc[s.index[s], "session_key"].nunique(),
            ),
            contactus_after_blog_sessions=(
                "reached_contactus_after_blog",
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
    by_blog["scheduledemo_after_rate"] = by_blog.apply(
        lambda r: pct(r["scheduledemo_after_blog_sessions"], r["unique_sessions"]), axis=1
    )
    by_blog["contactus_after_rate"] = by_blog.apply(
        lambda r: pct(r["contactus_after_blog_sessions"], r["unique_sessions"]), axis=1
    )

    by_blog = by_blog.sort_values(["unique_sessions", "blog_pageviews"], ascending=False)

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
        "scheduledemo_after_blog_sessions",
        "scheduledemo_after_rate",
        "contactus_after_blog_sessions",
        "contactus_after_rate",
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
            "scheduledemo_after_rate": st.column_config.NumberColumn("Schedule demo after rate", format="%.1f%%"),
            "contactus_after_rate": st.column_config.NumberColumn("Contact us after rate", format="%.1f%%"),
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
    ] = "This blog sends readers toward pricing. Consider using it as a commercial SEO asset."
    opportunity.loc[
        (opportunity["unique_sessions"] >= 3) & (opportunity["scheduledemo_after_rate"] >= 20),
        "opportunity_note",
    ] = "This blog sends readers toward schedule demo. Strengthen demo-oriented CTAs and internal links."
    opportunity.loc[
        (opportunity["unique_sessions"] >= 3) & (opportunity["contactus_after_rate"] >= 20),
        "opportunity_note",
    ] = "This blog sends readers toward contact us. Consider adding contact-oriented CTAs or sales-assist links."
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
                    "scheduledemo_after_rate",
                    "contactus_after_rate",
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
                "scheduledemo_after_rate": st.column_config.NumberColumn("Schedule demo after rate", format="%.1f%%"),
                "contactus_after_rate": st.column_config.NumberColumn("Contact us after rate", format="%.1f%%"),
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

tab_sessions, tab_blogs, tab_journey = st.tabs(["Session table", "Blogs", "Journey Sankey"])

with tab_sessions:
    render_overview_table(filtered_df, df)

with tab_blogs:
    render_blogs_page(filtered_df)

with tab_journey:
    render_journey_sankey_page(filtered_df)
