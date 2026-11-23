# InflationLens
Your groceries. Your prices. Your real inflation.

Personal grocery inflation tracker that compares your own receipts with official CPI (India MoSPI default, US BLS optional).

InflationLens is a Streamlit app for exploring grocery price changes using receipt line items and official CPI data.
## Current features
- Initialize and inspect the SQLite database
- Upload JPG, PNG, or PDF receipts
- OCR and parse receipt totals and line items
- Save, verify, and track product prices
- View personal price history and inflation analytics
- Import official CPI observations from CSV

## Quick start (Windows PowerShell)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    Copy-Item .env.example .env
    pip install -r requirements.txt
    pytest -v
    streamlit run app.py

## Public demo privacy
`PUBLIC_DEMO=true` is the default. In this mode, receipt OCR happens in memory, and parsed items remain only in the current browser session. They are not written to the shared database or receipt folder. CPI imports are disabled. Do not upload sensitive receipts to any public service.

For private local use, set `PUBLIC_DEMO=false` in `.env`. Do not turn this off on a public deployment without adding authentication and user-specific data isolation.

## Deploy on Streamlit Community Cloud
1. Sign in at [share.streamlit.io](https://share.streamlit.io/) with the GitHub account that can access this repository.
2. Select **Create app**, choose `manushreechikane/inflation_tracker`, branch `main`, and file `app.py`.
3. Keep the default public demo mode enabled and deploy.

The root `packages.txt` installs Tesseract and Poppler on the hosting container for receipt OCR. The repository must contain the latest app code before deployment.
