# InflationLens

**Your groceries. Your prices. Your real inflation.**

InflationLens is a Streamlit application that turns grocery receipts into personal price history. It uses OCR to extract purchases, SQLite to store verified records, and Plotly to compare changes across products and against official CPI data.

## Features

- Upload JPG, PNG, or PDF grocery receipts
- Extract purchase dates, totals, and line items with Tesseract OCR
- Correct OCR results before saving or analysis
- Store verified products and purchase history in SQLite
- Track monthly product prices and personal inflation
- Import official CPI observations from CSV
- Inspect database and OCR system status
- Process public-demo receipts entirely in the browser session

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Streamlit |
| Data | pandas, NumPy, Plotly |
| Database | SQLite, SQLAlchemy |
| OCR | Tesseract, pytesseract, PDF2Image |
| Image processing | Pillow, OpenCV |
| Testing | pytest |
| Deployment | Streamlit Community Cloud |

## Architecture

```text
Streamlit UI
    |
    +-- Receipt processing -> OCR -> parsed fields -> verified items
    |
    +-- Analytics -> monthly medians -> earliest/latest price change
    |
    +-- SQLAlchemy -> SQLite receipts, products, items, and CPI
```

## Privacy modes

`PUBLIC_DEMO=true` is the default. Uploaded receipts are processed in memory and saved only to `st.session_state`; they are not written to the shared database or receipt folder. CPI imports are disabled.

Set `PUBLIC_DEMO=false` in `.env` for private local use. In a public deployment, keep demo mode enabled and do not disable it until authentication and per-user data isolation are implemented.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Tesseract is required for OCR. On Windows, set `TESSERACT_CMD` in `.env` to the installed executable, for example `C:\Program Files\Tesseract-OCR\tesseract.exe`.

## Testing

The test suite verifies SQLite table creation, foreign-key enforcement, transaction rollback, duplicate receipt protection, receipt parsing, product normalization, and personal inflation calculations.

```powershell
python -m pytest -q
```

## Deploy on Streamlit Community Cloud

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) with the GitHub account that can access this repository.
2. Select **Create app**, choose this repository, branch `main`, and file `app.py`.
3. Keep `PUBLIC_DEMO=true` enabled.
4. Deploy and verify receipt upload and system status pages.

The root `packages.txt` installs Tesseract and Poppler on the hosting container. The repository must contain the latest app code before deployment.
