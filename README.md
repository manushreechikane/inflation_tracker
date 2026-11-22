# InflationLens
Your groceries. Your prices. Your real inflation.

Personal grocery inflation tracker that compares your own receipts with official CPI (India MoSPI default, US BLS optional).

Status: Phase 1 (foundation) complete. Full README is written in Phase 8.

## Quick start (Windows PowerShell)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    Copy-Item .env.example .env
    pip install -r requirements.txt
    pytest -v
    streamlit run app.py
