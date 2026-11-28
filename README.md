# InflationLens

**Your groceries. Your prices. Your real inflation.**

National CPI describes an average household. InflationLens describes yours: photograph a
grocery receipt, correct what the OCR misread, and the app builds a price history for the
exact products you buy — then puts your basket next to official CPI, rebased to the same
month so the two lines are actually comparable.

## What it does

| Screen | What it answers |
|---|---|
| **This month** | How much has my basket moved, weighted by what I spend? What rose fastest? |
| **Add a receipt** | Read a photo or PDF, correct the extracted lines, see what the OCR was unsure about, save. |
| **My basket** | Every tracked product, shrinkflation alerts, store-to-store spread, receipt management. |
| **vs. CPI** | Your index against an official series on one axis, plus the category gap. |
| **Data** | CSV export, CPI import / BLS fetch, demo reset, diagnostics. |

### The parts that matter

- **Weighted basket index.** Fixed quantities from your first month, rebased to 100, so the
  line answers "what would my usual basket cost now?" rather than "how did my shopping mix change?".
- **Product identity by pack.** `Milk 500 ml` and `Milk 1 L` are different products, which is
  what makes the next item possible.
- **Shrinkflation watch.** Price per 100 g / 100 ml across pack-size changes. A pack that
  loses weight at the same shelf price is caught, not hidden by the headline price.
- **Alias learning.** Rename `MLK TONED 500` to `Amul Toned Milk 500 ml` once and the old
  spelling is remembered for every future receipt.
- **OCR confidence.** Tesseract's per-line confidence is kept, low-confidence lines are
  surfaced for review, and the receipt image sits beside the editable table.
- **Receipt-style parsing.** Indian lakh separators (`1,29,999.50`), decimal commas, quantity
  lines (`2 x Bread 120.00`), discount/tax lines, totals printed with an item count, PDFs,
  and five date formats.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Tesseract is required for OCR. On Windows set `TESSERACT_CMD` in `.env`; on Debian/Ubuntu
`sudo apt-get install tesseract-ocr poppler-utils` (both are listed in `packages.txt`).

If Tesseract is missing the app still runs: the receipt screen says so and lets you type the
lines in by hand.

## Modes

`PUBLIC_DEMO=true` (the default) is the portfolio/demo mode:

- the app opens on a seeded nine-month grocery basket, so there is something to look at
- uploaded receipts are OCR'd in memory and stored only in `st.session_state`
- nothing is written to the database, and CPI imports are disabled (the CPI screen uses a
  clearly-labelled **illustrative** series so the comparison still works)

Set `PUBLIC_DEMO=false` in `.env` for a private local instance backed by SQLite. Seed it with
nine months of sample receipts from the Data screen, or from the shell:

```bash
python -m modules.data_management.seed
```

Do not ship a multi-user deployment with demo mode off until per-user isolation exists — one
SQLite file means one shared basket for everybody.

## How it fits together

```text
app.py                    sidebar navigation, mobile pill bar, page dispatch
ui/theme.py               the stylesheet and formatting helpers
ui/charts.py              one sparse chart language (no grids, no legends)
ui/data.py                the single data layer: demo session <-> SQLite
ui/pages.py               the five screens
modules/receipt_processing/
  receipt_processor.py    OCR lines + confidence, money/date/pack parsing
  sample_receipts.py      rendered sample receipts for the demo
modules/data_management/
  models.py               receipts, products, aliases, items, CPI observations
  repository.py           product identity, alias learning, CPI upserts
  seed.py                 the nine-month demo basket
modules/analytics/         tidy history frame -> change, index, shrinkflation, spread
modules/inflation/         the public inflation API
modules/external_data/     BLS API, CSV import, bundled sample series
```

Every calculation works on one DataFrame:

```text
receipt_id, purchase_date, product, product_id, category, brand,
package_size, package_unit, quantity, unit_price, total_price, store_name
```

The demo path builds it from `st.session_state`, the private path from SQL, and both then run
through the same analytics. There is no second implementation to keep in sync.

## Official CPI

- **United States** — BLS public API v2. Set `BLS_API_KEY` for a higher daily limit, or leave
  it empty for the anonymous limit. Series ids live in `modules/external_data/cpi.py`.
- **India** — import a CSV with `period` and `index_value` (optional `category`, `series_id`,
  `source`). MoSPI does not offer a stable public JSON API.

The bundled series (`SAMPLE-FOOD`) is generated from a fixed annual rate. It is labelled as a
sample everywhere it appears and is not a published statistic.

## Reading the numbers honestly

- Change is *first observed month → last observed month* within the selected window, using
  monthly medians. It is not a seasonally adjusted index.
- Weights are fixed at the first month's spend, so the index measures prices, not changes in
  what you bought.
- A product needs two observations before it appears in any change figure.
- OCR misreads happen. The verification screen exists because of that, and every number is
  only as good as the corrected lines.

## Tests

```bash
python -m pytest -q
```

Covers: schema constraints and cascades, product identity and alias learning, receipt parsing
(separators, quantities, discounts, totals, dates, pack sizes), the analytics pipeline
(weighting, index, shrinkflation, store spread, CPI rebasing), BLS/CSV parsing, the demo seed,
and a Streamlit `AppTest` smoke run of all five screens. The OCR round-trip tests skip
themselves when Tesseract is absent.

## Deploy on Streamlit Community Cloud

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) with access to this repository.
2. **Create app** → repository, branch `main`, file `app.py`.
3. Keep `PUBLIC_DEMO=true` unless you have added authentication.
4. Deploy and check the receipt upload and the basket screens.

`packages.txt` installs Tesseract and Poppler in the container. Note that the hosted file
system is ephemeral: a private instance loses its SQLite file on redeploy.

## Known limits

- Single user, single SQLite file. No auth, no per-user isolation, no migrations.
- OCR is Tesseract only; handwriting and crumpled thermal paper are out of scope.
- Store and product names are whatever the receipt printed.
- Currency formatting follows `DEFAULT_CURRENCY`; no FX conversion.

## License

MIT — see [LICENSE](LICENSE).
