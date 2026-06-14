# inbound-dashboard

A single-page Streamlit dashboard for analyzing inbound website traffic, sources, geographies, landing pages, and user journeys.

## Files

- `app.py` - Streamlit app
- `bq-results-20260609-135014-1781013034663.csv` - default traffic dataset
- `requirements.txt` - Python dependencies

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage

The app loads the bundled CSV by default when present in the same folder. You can also upload a fresh CSV from the sidebar.

Use the filters at the top of the dashboard to narrow rows by date, landing type, source, medium, country, region, city, landing page, and text search across journey/source fields.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository named `inbound-dashboard`.
2. In Streamlit Community Cloud, create a new app from that repo.
3. Set the main file path to `app.py`.
4. Deploy.

