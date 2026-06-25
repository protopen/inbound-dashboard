# inbound-dashboard

A Streamlit dashboard for analyzing inbound website traffic, blog journeys, website-wide drop-offs, and inbound form submissions.

## Files

- `app.py` - Streamlit app
- `bq-results-20260609-135014-1781013034663.csv` - website traffic dataset
- `requirements.txt` - Python dependencies
- `.streamlit/secrets.toml.example` - Supabase secrets template

The Inbound Leads dashboard now reads directly from Supabase instead of a bundled Excel/CSV source.

## Run locally

```bash
pip install -r requirements.txt
```

Create a local secrets file:

```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://rdhnojmvamxkwirsnzue.supabase.co"
anon_key = "PASTE_YOUR_SUPABASE_ANON_KEY_HERE"
inbound_leads_table = "Inbound-Form-Submissions"
```

Do not commit `.streamlit/secrets.toml`. It is ignored by `.gitignore`.

Run the app:

```bash
streamlit run app.py
```

## Navigation

The left sidebar opens with **Inbound Leads** selected by default. Use the sidebar radio buttons to switch between **Inbound Leads** and **Website Traffic**.

## Inbound Leads

The `Inbound Leads` dashboard loads form submissions from Supabase.

Expected Supabase columns:

- `id`
- `created_at`
- `Page Path`
- `Form Type`
- `Name`
- `Email`
- `Company Name`
- `Company URL`
- `How did they find us`
- `Message`
- `raw`
- `Intent Type`
- `Phone Number`
- `Business Type`
- `Monthly Order Volume`

Rows with a populated `Phone Number` are excluded from included submission metrics and counted under **Phone rows removed**.

The dashboard includes:

- Included submissions
- Prospective merchant queries
- Customer queries
- Spam queries
- Phone rows removed
- Intent split with counts and shares
- Prospective merchant query month-over-month line chart
- Monthly trend by intent type
- Merchant share and merchant month-over-month growth
- Filtered submission rows with CSV download

The Inbound Leads page filters include date range, intent type, form type, and page path.

## Website Traffic

The app loads the bundled website traffic CSV from the same folder as the app. The current bundled traffic source contains 12,489 sessions through June 15, 2026.

Use the compact filters at the top of the dashboard to narrow rows by date, landing type, source, medium, country, region, city, landing page, and text search across journey/source fields. United States and Canada are selected by default in the country filter when available.

Website traffic tabs:

- `Session table` shows the filtered raw session-level rows.
- `Blogs` analyzes sessions that include `/blog/...` pages or the `/blogs` index. It reports blog sessions and post-blog movement to pricing, schedule demo, and contact us pages, along with source mix, next-page behavior, and opportunity flags.
- `Journey Sankey` is a website-wide drop-off view built from `page_sequence`. It shows landing-page movement across journey steps, explicit drop-off nodes at each step, drop-off by step, highest drop-off pages, and a downloadable flow table.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository named `inbound-dashboard`.
2. In Streamlit Community Cloud, create a new app from that repo.
3. Set the main file path to `app.py`.
4. Add the Supabase values under the app's **Secrets** settings using the same TOML format shown above. The project URL is already filled in; paste the anon key in the `anon_key` field.
5. Deploy.
