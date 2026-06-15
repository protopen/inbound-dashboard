# inbound-dashboard

A Streamlit dashboard for analyzing inbound website traffic, blog journeys, website-wide drop-offs, and organic inbound form submissions.

## Files

- `app.py` - Streamlit app
- `bq-results-20260609-135014-1781013034663.csv` - default website traffic dataset
- `organic_form_submissions_clean_dashboard_fixed (1).csv` - default inbound leads dataset
- `requirements.txt` - Python dependencies

## Navigation

The left sidebar opens with **Inbound Leads** selected by default. Use the sidebar radio buttons to switch between **Inbound Leads** and **Website Traffic**.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Navigation

The top navigation has two dashboard options:

- `Website Traffic` opens the existing traffic dashboard.
- `Inbound Leads` opens the organic form submissions dashboard.

## Website Traffic

The app loads the bundled website traffic CSV by default when present in the same folder. You can also upload a fresh website traffic CSV from the sidebar.

Use the compact filters at the top of the dashboard to narrow rows by date, landing type, source, medium, country, region, city, landing page, and text search across journey/source fields. United States and Canada are selected by default in the country filter when available.

Website traffic tabs:

- `Session table` shows the filtered raw session-level rows.
- `Blogs` analyzes sessions that include `/blog/...` pages or the `/blogs` index. It reports unique sessions by blog path, landing/exit behavior, next-page behavior, source mix, and post-blog movement to pricing, schedule demo, and contact us pages.
- `Journey Sankey` is a website-wide drop-off view built from `page_sequence`. It shows landing-page movement across journey steps, explicit drop-off nodes at each step, drop-off by step, highest drop-off pages, and a downloadable flow table.

## Inbound Leads

The `Inbound Leads` dashboard loads the bundled organic form submissions CSV by default. You can also upload a fresh inbound leads CSV from the sidebar.

It includes:

- Included submissions
- Prospective merchant queries
- Customer queries
- Spam queries
- Phone rows removed
- Intent split with counts and shares
- Monthly trend by intent type
- Prospective merchant query month-over-month line chart
- Merchant share and merchant month-over-month growth
- Filtered submission rows with CSV download

The Inbound Leads page filters include date range, intent type, form type, and page path.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository named `inbound-dashboard`.
2. In Streamlit Community Cloud, create a new app from that repo.
3. Set the main file path to `app.py`.
4. Deploy.
