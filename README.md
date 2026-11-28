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
| **My plan** | A coach that turns the basket into a plan against your budget: what to cap, what to swap, what to stop assuming. |
| **You** | Account and profile: picture, name, household, budget, currency, password, data export, deletion. |
| **Data** | CSV export, CPI import / BLS fetch, sample-basket reload, diagnostics. |

Signing in is part of the product, not a wrapper: each account keeps its own basket, profile
and plan, so several people can use one deployment without seeing each other's prices.

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

## Accounts

Every visit starts on a sign-in screen. An account has:

- an email and password (PBKDF2-HMAC-SHA256, 210,000 iterations, a per-user salt; the plain
  password is never stored, logged or emailed)
- a profile: display name, picture, country, currency, monthly grocery budget, household size
  and a one-line goal
- **its own basket.** Receipts and the price history belong to the account, not the browser,
  so two people on one deployment never share a basket and a basket follows you to another
  device
- a password change, a CSV export and account deletion (basket included)

A new account is seeded with nine months of sample receipts so the app is never empty. The
sample basket can be reloaded from **Data**, and the "Look around with a sample account"
button creates a throwaway account for a reviewer who does not want to sign up.

Accounts, profiles and baskets live in one SQLite file (`data/inflationlens.db`). On a free
container that file survives as long as the container does, so treat it as a demo store: there
is no email verification and no password reset, and anyone with the link can create an
account. It is authentication for a portfolio app, not for anything sensitive.

`PUBLIC_DEMO=true` (the default) additionally disables CPI imports and serves the
clearly-labelled **illustrative** CPI series, so the comparison still works offline. Set
`PUBLIC_DEMO=false` in `.env` to import real CPI rows or fetch them from BLS (see below).

## How it fits together

```text
app.py                    sign-in gate, sidebar navigation, mobile pill bar, dispatch
ui/theme.py               the stylesheet and formatting helpers
ui/charts.py              one sparse chart language (no grids, no legends)
ui/auth.py                sign in, sign up, sample account, session handling
ui/data.py                the single data layer, scoped to the signed-in account
ui/pages.py               the five price screens
ui/profile.py             profile, budget, password, export, deletion
ui/coach.py               the plan builder and its chat
modules/receipt_processing/
  receipt_processor.py    OCR lines + confidence, money/date/pack parsing
  sample_receipts.py      rendered sample receipts for the demo
modules/data_management/
  accounts.py             accounts, PBKDF2 passwords, profiles, per-user baskets
  models.py               accounts, baskets, receipts, products, aliases, CPI observations
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

The account basket is read into that frame and run through the same analytics as any SQL
path, so there is no second implementation to keep in sync.

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
