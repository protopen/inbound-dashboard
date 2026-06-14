# inbound-dashboard

A Streamlit dashboard for analyzing inbound website traffic, journeys, sources, geographies, and blog-page performance.

## What's included

- `app.py` — Streamlit app
- `bq-results-20260609-135014-1781013034663.csv` — default inbound traffic CSV
- `requirements.txt` — Python dependencies

## Features

### Session table

- CSV upload option in the sidebar
- Date range filter
- Filters for landing type, session medium, session source, country, region, city, and landing page
- Text search across page sequence, events, source, and geo fields
- Summary metrics
- Full filtered session table
- Download filtered CSV

### Blogs tab

- Detects blog pages from `/blog/...` and `/blogs`
- Shows unique sessions for each blog path
- Calculates blog pageviews, landing sessions, exit sessions, pricing-after-blog sessions, journey position, average pages/session, top source, top medium, top country, and top next page
- Shows top blog paths by unique sessions
- Shows blog source mix and next-page behavior
- Adds automatic SEO opportunity flags
- Download blog path analysis CSV

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will auto-load `bq-results-20260609-135014-1781013034663.csv` if it is in the same folder as `app.py`. You can also upload a CSV from the sidebar.
