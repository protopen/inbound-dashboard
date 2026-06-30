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

Rows with a populated `Phone Number` are included in live Home tables, filters, metrics, and CSV downloads; they are no longer excluded from the dashboard.

The Inbound Leads section has two tabs:

- `Home` shows all live inbound lead rows returned from Supabase.
- `Historical Data` shows the hard-coded legacy summary for submissions up to and including June 15, 2026.

The `Home` tab includes live Supabase filters for date range, intent type, form type, and page path. It does not hard-split data by June 15. The date filter uses normalized `created_at` timestamps from Supabase, defaults to June 1, 2026 through the latest available date when possible, and the intent type dropdown is populated dynamically from the unique `Intent Type` values currently returned by Supabase.



The live `Home` trend chart has a `Daily` / `Monthly` toggle. `Daily` is selected by default and plots prospective merchant queries by day for the active date range. `Monthly` keeps the previous month-over-month view with merchant share and MoM growth.

The `Historical Data` tab is not live-filtered. It shows the legacy hard-coded dashboard from the prior spreadsheet summary, including:

- Included submissions
- Prospective merchant queries
- Customer queries
- Spam queries
- Intent split with counts and shares
- Monthly included submissions by intent
- Prospective merchant query month-over-month line chart
- Monthly trend by intent type
- Merchant share and merchant month-over-month growth

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


## Supabase troubleshooting

If the Inbound Leads page shows `No inbound lead rows were returned from Supabase`, the most common cause is Row Level Security blocking reads for the anon key. For a private internal dashboard, prefer using the Supabase `service_role_key` in Streamlit secrets:

```toml
[supabase]
url = "https://rdhnojmvamxkwirsnzue.supabase.co"
service_role_key = "PASTE_YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE"
inbound_leads_table = "Inbound-Form-Submissions"
```

Do not commit `.streamlit/secrets.toml` to GitHub.

If you want to keep using the anon key, add a SELECT policy in Supabase for the table. Only do this if you are comfortable with the access pattern:

```sql
create policy "Allow dashboard read access"
on public."Inbound-Form-Submissions"
for select
using (true);
```

### Date parsing note
The Inbound Leads dashboard normalizes Supabase/Postgres timestamps with mixed precision, including `2026-05-01 12:50:00+00` and `2026-06-25 10:22:37.533225+00`, plus ISO variants with `T`, `Z`, `+00`, `+0000`, or `+00:00` timezone suffixes, before applying date filters. The date-range widget key also changes when the loaded min/max dates change, so Streamlit does not keep an old cached range after new rows are added.

## Intent normalization

The live Inbound Leads dashboard clubs `Lead B2B` and `Prospective Merchant Query` into a single displayed intent: `Prospective Merchant Query`. This affects KPIs, filters, intent split, daily trend, monthly trend, tables, and CSV downloads.
