"""The five screens, written as one narrative rather than a dashboard.

Order matters: this month -> add a receipt -> your basket -> against official
CPI -> data. Each answer creates the next question.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from config import settings
from config.constants import GROCERY_CATEGORIES, SUPPORTED_COUNTRIES
from modules.analytics.analytics import (
    basket_change,
    basket_index,
    category_breakdown,
    cpi_rebased,
    cpi_series_options,
    personal_inflation,
    shrinkflation,
    spend_by_month,
    store_spread,
)
from modules.external_data.cpi import BLS_SERIES, fetch_bls, parse_cpi_csv
from modules.receipt_processing.receipt_processor import (
    ocr_lines_from_bytes,
    parse_pack,
    parse_receipt_lines,
)
from modules.receipt_processing.sample_receipts import SAMPLE_NAMES, render_sample
from ui import charts, data, theme




# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #

def flash(title: str, body: str = "") -> None:
    st.session_state["flash"] = (title, body)


def render_flash() -> None:
    payload = st.session_state.pop("flash", None)
    if payload:
        title, body = payload if isinstance(payload, tuple) else (payload, "")
        st.success(f"**{title}** {body}".strip())


def window_selector(key: str = "") -> int | None:
    """The sidebar owns the window control; screens only read the value."""
    return st.session_state.get("months") or None


def current_country() -> str:
    return st.session_state.get("country", settings.DEFAULT_COUNTRY)


def pack_label(size, unit) -> str:
    if size is None or unit is None:
        return ""
    size = float(size)
    if unit in {"g", "ml"} and size >= 1000:
        return f"{size / 1000:g} {'kg' if unit == 'g' else 'L'}"
    return f"{size:g} {unit}"


def _series_default(cpi: pd.DataFrame) -> str | None:
    options = cpi_series_options(cpi)
    if not options:
        return None
    for series_id, label in options:
        if "all items" in label.lower():
            return series_id
    return options[0][0]


# --------------------------------------------------------------------------- #
# 1. This month
# --------------------------------------------------------------------------- #

def page_overview() -> None:
    months = window_selector("window_overview")
    history_frame = data.history(months)
    if history_frame.empty:
        theme.hero("Your basket", "—", "No receipts yet. One grocery bill is enough to start.", unit="")
        theme.empty("Nothing to measure yet.", "Open “Add a receipt” and drop in a photo.")
        return

    inflation = personal_inflation(history_frame)
    index = basket_index(history_frame)
    change = basket_change(inflation)
    spend = float(history_frame["total_price"].sum())
    products = int(history_frame["product"].nunique())
    receipts_total = data.receipt_count()

    cpi, is_sample = data.cpi_frame(current_country())
    series_id = _series_default(cpi)
    first_month = index.iloc[0]["month"] if not index.empty else None
    last_month = index.iloc[-1]["month"] if not index.empty else None
    official = cpi_rebased(cpi, first_month, series_id) if first_month else pd.DataFrame()
    official_change = (
        round(float(official.iloc[-1]["index"]) - 100, 1) if not official.empty else None
    )

    if change is None:
        theme.hero(
            "Your basket", "—",
            f"Tracking {products} products. A second month of receipts unlocks the change.",
            unit="",
        )
    else:
        span = f"{theme.month_label(first_month)} → {theme.month_label(last_month)}"
        comparison = ""
        if official_change is not None:
            tense = "more" if change > official_change else "less"
            sample_chip = (' <span class="il-chip il-chip--sample">sample</span>'
                           if is_sample else "")
            comparison = (
                f"Official CPI over the same months: <b>{official_change:+.1f}%</b>"
                f"{sample_chip}. You are <b>{abs(change - official_change):.1f} points {tense}</b>."
            )
        theme.hero(
            f"Your basket · {span}",
            f"{change:+.1f}",
            f"Inflation across the {products} products you buy, weighted by what you spend on each.",
            sub=comparison,
        )

    movers = inflation.head(1)
    kpis = [
        ("Spent", theme.compact_money(spend), f"across {receipts_total} receipts"),
        ("Tracked products", str(products), f"{len(inflation)} with repeat prices"),
        ("Basket change", theme.signed(change), "since the first month"),
        ("Biggest riser", movers.iloc[0]["product"] if not movers.empty else "—",
         theme.signed(movers.iloc[0]["change_pct"]) if not movers.empty else "no data"),
    ]
    theme.kpis(kpis)

    theme.section("Your basket against official CPI", "index, first month = 100")
    if index.empty or index["month"].nunique() < 2:
        theme.note("A single month is a starting point, not a trend. Add last month's receipts too.")
    st.plotly_chart(
        charts.index_chart(index, official),
        use_container_width=True,
        config=charts.CHART_CONFIG,
    )
    if is_sample:
        theme.note(
            "The dotted line is a bundled <b>illustrative</b> series, not official statistics — "
            "import real CPI on the Data screen to replace it."
        )

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        theme.section("What moved", "first vs. latest purchase")
        st.plotly_chart(
            charts.movers_chart(inflation), use_container_width=True, config=charts.CHART_CONFIG
        )
    with right:
        theme.section("Spend by month", "")
        st.plotly_chart(
            charts.spend_chart(spend_by_month(history_frame)),
            use_container_width=True, config=charts.CHART_CONFIG,
        )
        theme.note("Prices are what the receipts said; the mix of what you bought still moves this bar.")

    theme.section("Recent receipts", "newest first")
    table = data.receipt_table()
    if table.empty:
        theme.empty("No receipts stored yet.")
    else:
        st.dataframe(
            table.head(6),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "Total": st.column_config.NumberColumn(
                    "Total", format=f"{theme.currency_symbol()}%.2f"
                ),
            },
        )


# --------------------------------------------------------------------------- #
# 2. Add a receipt
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner="Reading the receipt…")
def _parse_cached(name: str, blob: bytes) -> dict:
    return parse_receipt_lines(ocr_lines_from_bytes(name, blob))


def page_scan() -> None:
    theme.section("Add a receipt", "photo in · prices out")
    if data.is_demo():
        theme.note(
            "Demo mode: this is <b>your</b> copy of the sample basket. A receipt you add "
            "stays in your own workspace — never in someone else's — and is still here when "
            "you come back to this link."
        )

    source = st.radio(
        "Source", ["Upload a file", "Try a sample"],
        horizontal=True, label_visibility="collapsed", key="scan_source",
    )

    payload: tuple[str, bytes] | None = None
    if source == "Try a sample":
        choice = st.selectbox(
            "Sample receipt", list(SAMPLE_NAMES),
            format_func=lambda key: SAMPLE_NAMES[key], key="scan_sample",
        )
        payload = (f"{choice}.png", render_sample(choice))
    else:
        upload = st.file_uploader(
            "Receipt", type=["jpg", "jpeg", "png", "pdf"], key="scan_upload",
            label_visibility="collapsed",
        )
        if upload is not None:
            payload = (upload.name, upload.getvalue())

    if payload is None:
        theme.steps([
            ("Photograph the whole bill",
             "Get the store name, the date and the total line in frame. The total is used "
             "as a checksum against the items."),
            ("Fix what the reader guessed",
             "Every line is editable before it is saved. Names you correct are remembered "
             "for the next receipt from that shop."),
            ("Watch your own index",
             "Prices are weighted by what you actually spend, then compared with official "
             "CPI on the same axis."),
        ])
        return

    name, blob = payload
    if len(blob) > settings.MAX_UPLOAD_BYTES:
        st.error(f"That file is larger than {settings.MAX_UPLOAD_MB} MB.")
        return

    try:
        parsed = _parse_cached(name, blob)
    except Exception as exc:
        st.error(f"Could not read that receipt: {exc}")
        parsed = parse_receipt_lines([])

    items = parsed["items"] or [{
        "ocr_product_name": "", "quantity": 1.0, "ocr_total_price": 0.0,
        "package_size": None, "package_unit": None, "category": "Other",
        "ocr_confidence": None, "ocr_line_text": "",
    }]
    rows = pd.DataFrame([{
        "Product": item["ocr_product_name"],
        "Qty": float(item.get("quantity") or 1),
        "Line price": float(item.get("ocr_total_price") or 0),
        "Pack": pack_label(item.get("package_size"), item.get("package_unit")),
        "Category": item.get("category") or "Other",
        "OCR": item.get("ocr_confidence"),
    } for item in items])

    left, right = st.columns([0.8, 1.2], gap="large")
    with left:
        if name.lower().endswith(".pdf"):
            theme.empty("PDF receipt", "Parsed from the document's pages.")
        else:
            st.image(blob, use_container_width=True)
        if parsed["ocr_confidence"] is not None:
            theme.note(f"Average OCR confidence: <b>{parsed['ocr_confidence']:.0f}%</b>")
        uncertain = [item for item in parsed["items"]
                     if item.get("ocr_confidence") is not None and item["ocr_confidence"] < 65]
        if uncertain:
            with st.expander(f"{len(uncertain)} lines to double-check"):
                for item in uncertain:
                    st.markdown(
                        f"`{theme.esc(item['ocr_line_text'])}` — "
                        f"{item['ocr_confidence']:.0f}% · read as **{theme.esc(item['ocr_product_name'])}** "
                        f"at {theme.money(item['ocr_total_price'])}"
                    )

    with right:
        gap = parsed["line_item_gap"]
        if gap is not None and abs(gap) > 0.05:
            theme.alert(
                "The lines do not add up to the printed total",
                f"Items sum to {theme.money(parsed['items_total'])} but the receipt says "
                f"{theme.money(parsed['receipt_total'])}. Check for a missing line or a discount.",
            )

        stored_total = parsed["receipt_total"] or parsed["items_total"]
        with st.form("receipt_form", clear_on_submit=False):
            store = st.text_input("Store", value=parsed["store_name"] or "")
            date_col, total_col = st.columns(2)
            purchase_date = date_col.date_input(
                "Purchase date", value=parsed["purchase_date"] or date.today()
            )
            receipt_total = total_col.number_input(
                f"Receipt total ({theme.currency_symbol()})",
                min_value=0.0, value=float(stored_total or 0), step=1.0,
            )
            edited = st.data_editor(
                rows,
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                disabled=["OCR"],
                key=f"items_{name}",
                column_config={
                    "Product": st.column_config.TextColumn("Product", width="large"),
                    "Qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
                    "Line price": st.column_config.NumberColumn(
                        f"Line price ({theme.currency_symbol()})", min_value=0.0, format="%.2f"
                    ),
                    "Pack": st.column_config.TextColumn("Pack", help="500 ml, 1 kg, 6 pcs"),
                    "Category": st.column_config.SelectboxColumn(
                        "Category", options=GROCERY_CATEGORIES
                    ),
                    "OCR": st.column_config.NumberColumn("OCR", format="%.0f"),
                },
            )
            submitted = st.form_submit_button("Save this receipt", type="primary")

    if submitted:
        cleaned: list[dict] = []
        for row in edited.to_dict("records"):
            product = str(row.get("Product") or "").strip()
            price = float(row.get("Line price") or 0)
            quantity = float(row.get("Qty") or 1) or 1.0
            if not product or price <= 0:
                continue
            size, unit = parse_pack(str(row.get("Pack") or ""))
            cleaned.append({
                "product": product,
                "quantity": quantity,
                "unit_price": round(price / quantity, 2),
                "total_price": round(price, 2),
                "package_size": size,
                "package_unit": unit,
                "category": str(row.get("Category") or "Other"),
                "ocr_confidence": row.get("OCR"),
                "user_corrected": True,
            })
        if not cleaned:
            st.error("Add at least one product with a price above zero.")
        else:
            try:
                data.save_receipt(
                    store_name=store.strip(),
                    purchase_date=purchase_date,
                    receipt_total=float(receipt_total) or sum(i["total_price"] for i in cleaned),
                    items=cleaned,
                    raw_text=parsed["raw_text"],
                    file_name=name,
                    file_bytes=blob,
                )
                flash("Receipt added.", f"{len(cleaned)} products from {store or 'that receipt'}.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save the receipt: {exc}")


# --------------------------------------------------------------------------- #
# 3. Your basket
# --------------------------------------------------------------------------- #

def page_basket() -> None:
    months = window_selector("window_basket")
    history_frame = data.history(months)
    if history_frame.empty:
        theme.empty("No verified purchases yet.", "Add a receipt first — the basket builds itself.")
        return

    inflation = personal_inflation(history_frame)
    packs = history_frame.groupby("product").agg(
        package_size=("package_size", "last"),
        package_unit=("package_unit", "last"),
    )
    table = inflation.merge(packs, on="product", how="left") if not inflation.empty else inflation

    theme.section("Tracked products", "change from first to latest purchase")
    if table.empty:
        theme.empty("Not enough history yet.", "Two purchases of the same product unlock a change.")
    else:
        display = pd.DataFrame({
            "Product": table["product"],
            "Category": table["category"].fillna("Other"),
            "Pack": [pack_label(s, u) for s, u in zip(table["package_size"], table["package_unit"])],
            "Obs": table["observations"],
            "First": table["base_price"],
            "Latest": table["latest_price"],
            "Change": table["change_pct"],
            "Share of spend": table["weight_pct"],
        })
        st.dataframe(
            display,
            hide_index=True,
            use_container_width=True,
            height=min(620, 36 * len(display) + 42),
            column_config={
                "Product": st.column_config.TextColumn("Product", width="medium"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Pack": st.column_config.TextColumn("Pack", width="small"),
                "Obs": st.column_config.NumberColumn("Obs", width="small"),
                "First": st.column_config.NumberColumn(
                    "First", width="small", format=f"{theme.currency_symbol()}%.2f"
                ),
                "Latest": st.column_config.NumberColumn(
                    "Latest", width="small", format=f"{theme.currency_symbol()}%.2f"
                ),
                "Change": st.column_config.NumberColumn(
                    "Change", width="small", format="%+.1f%%"
                ),
                "Share of spend": st.column_config.ProgressColumn(
                    "Spend share", width="small", min_value=0, max_value=100, format="%.0f%%"
                ),
            },
        )

        product = st.selectbox("Look at one product", display["Product"], key="basket_product")
        subset = history_frame[history_frame["product"] == product]
        row = table[table["product"] == product].iloc[0]
        st.plotly_chart(
            charts.product_line(subset),
            use_container_width=True, config=charts.CHART_CONFIG,
        )
        theme.note(
            f"{int(row['observations'])} purchases · {theme.money(row['base_price'])} → "
            f"{theme.money(row['latest_price'])} · "
            f"{theme.signed(row['change_pct'])} since {theme.month_label(row['base_month'])}"
        )

    theme.section("Shrinkflation watch", "same pack, less product")
    flags = shrinkflation(history_frame)
    flagged = flags[flags["flagged"]] if not flags.empty else flags
    if flagged.empty:
        theme.note("No pack changes detected. Nothing to report — yet.")
    else:
        for _, row in flagged.head(3).iterrows():
            size_move = row["size_change_pct"]
            unit_move = row["per_unit_change_pct"]
            theme.alert(
                f"{row['product']} — pack {size_move:+.0f}%, price per {row['unit_label']} {unit_move:+.0f}%",
                f"{row['base_size']:g} → {row['latest_size']:g} at "
                f"{theme.money(row['base_price'])} → {theme.money(row['latest_price'])}. "
                f"Per {row['unit_label']}: {theme.money(row['per_unit_base'])} → "
                f"{theme.money(row['per_unit_latest'])}.",
            )
        with st.expander("All pack-size comparisons"):
            view = flags[["product", "base_size", "latest_size", "size_change_pct",
                          "price_change_pct", "per_unit_change_pct", "unit_label"]]
            st.dataframe(view, hide_index=True, use_container_width=True)

    spread = store_spread(history_frame)
    if not spread.empty:
        theme.section("Store spread", "same product, different shelves")
        view = spread.rename(columns={
            "product": "Product", "store_name": "Store", "latest_price": "Latest",
            "last_seen": "Last seen", "vs_cheapest_pct": "Vs. cheapest",
        })
        st.dataframe(
            view, hide_index=True, use_container_width=True,
            column_config={
                "Latest": st.column_config.NumberColumn(
                    "Latest", format=f"{theme.currency_symbol()}%.2f"
                ),
                "Last seen": st.column_config.DateColumn("Last seen", format="DD MMM YYYY"),
                "Vs. cheapest": st.column_config.NumberColumn("Vs. cheapest", format="%+.1f%%"),
            },
        )

    theme.section("Correct a product", "names stick to the next receipt")
    products = data.product_options()
    if products:
        with st.expander("Rename or re-categorise"):
            target = st.selectbox("Product", products, key="fix_target")
            current_category = history_frame.loc[
                history_frame["product"] == target, "category"
            ].dropna()
            current_category = current_category.iloc[-1] if not current_category.empty else "Other"
            new_name = st.text_input("Display name", value=target, key="fix_name")
            category = st.selectbox(
                "Category", GROCERY_CATEGORIES,
                index=GROCERY_CATEGORIES.index(current_category)
                if current_category in GROCERY_CATEGORIES else len(GROCERY_CATEGORIES) - 1,
                key="fix_category",
            )
            if st.button("Save correction", key="fix_save"):
                try:
                    data.rename_product(target, new_name)
                    data.set_category(new_name, category)

                    flash("Product updated.", "The old spelling is remembered for next time.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        theme.note(
            "Renaming a product also teaches the parser: the spelling on your receipts "
            "is remembered and mapped to the new name."
        )

    theme.section("Receipts", "delete anything that was read wrong")
    table = data.receipt_table()
    if table.empty:
        theme.empty("No receipts stored.")
        return
    st.dataframe(
        table, hide_index=True, use_container_width=True,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            "Total": st.column_config.NumberColumn(
                "Total", format=f"{theme.currency_symbol()}%.2f"
            ),
        },
    )
    options = table["Receipt"].tolist()
    target = st.selectbox(
        "Remove a receipt", options, key="delete_receipt",
        format_func=lambda rid: (
            table.loc[table["Receipt"] == rid, "Date"].dt.strftime("%d %b %Y").iloc[0]
            + " · " + str(table.loc[table["Receipt"] == rid, "Store"].iloc[0])
        ),
    )
    if st.button("Delete receipt", key="delete_receipt_btn"):
        if data.delete_receipt(int(target)):
            flash("Receipt deleted.")
            st.rerun()
        else:
            st.error("That receipt no longer exists.")


# --------------------------------------------------------------------------- #
# 4. Against official CPI
# --------------------------------------------------------------------------- #

def page_cpi() -> None:
    months = window_selector("window_cpi")
    country = st.selectbox(
        "Country", list(SUPPORTED_COUNTRIES),
        index=list(SUPPORTED_COUNTRIES).index(current_country()),
        format_func=lambda code: SUPPORTED_COUNTRIES[code]["label"],
        key="cpi_country",
    )
    st.session_state["country"] = country

    history_frame = data.history(months)
    inflation = personal_inflation(history_frame)
    index = basket_index(history_frame)
    cpi, is_sample = data.cpi_frame(country)

    if index.empty:
        theme.empty("Nothing to compare yet.", "Your line needs at least one month of receipts.")
        return

    options = cpi_series_options(cpi)
    series_id = _series_default(cpi)
    if len(options) > 1:
        labels = dict(options)
        series_id = st.selectbox(
            "Official series", list(labels), index=list(labels).index(series_id),
            format_func=lambda key: labels[key], key="cpi_series",
        )

    official = cpi_rebased(cpi, index.iloc[0]["month"], series_id)
    official_change = (
        round(float(official.iloc[-1]["index"]) - 100, 1) if not official.empty else None
    )
    personal_change = basket_change(inflation)

    theme.hero(
        f"Your basket vs. {SUPPORTED_COUNTRIES[country]['label']} CPI",
        f"{personal_change:+.1f}" if personal_change is not None else "—",
        "since " + theme.month_label(index.iloc[0]["month"]),
        sub=(
            f"Official series over the same months: <b>{official_change:+.1f}%</b>"
            + (' <span class="il-chip il-chip--sample">sample data</span>' if is_sample else "")
            if official_change is not None else "No official series available yet."
        ),
    )

    st.plotly_chart(
        charts.index_chart(index, official),
        use_container_width=True, config=charts.CHART_CONFIG,
    )
    if is_sample:
        theme.note(
            "This comparison uses the bundled <b>illustrative</b> series so the demo works offline. "
            "It is not a published statistic. Import real CPI on the Data screen."
        )

    if not inflation.empty:
        breakdown = category_breakdown(inflation)
        gap = (
            round(float(breakdown["change_pct"].iloc[-1]), 1) if not breakdown.empty else None
        )
        theme.section("Where the difference comes from", "your categories, weighted by spend")
        left, right = st.columns([1, 1], gap="large")
        with left:
            st.plotly_chart(
                charts.category_chart(breakdown),
                use_container_width=True, config=charts.CHART_CONFIG,
            )
        with right:
            view = breakdown.rename(columns={
                "category": "Category", "weight_pct": "Share of spend",
                "change_pct": "Your change", "products": "Products",
            })
            if official_change is not None:
                view["Gap vs. official"] = (view["Your change"] - official_change).round(1)
            st.dataframe(
                view, hide_index=True, use_container_width=True,
                column_config={
                    "Your change": st.column_config.NumberColumn("Your change", format="%+.1f%%"),
                    "Gap vs. official": st.column_config.NumberColumn(
                        "Gap vs. official", format="%+.1f%%"
                    ),
                    "Share of spend": st.column_config.NumberColumn(
                        "Share of spend", format="%.0f%%"
                    ),
                },
            )
        theme.note(
            "A gap is not an error. Official indices weight thousands of goods; yours weights "
            "what your household actually buys, at the shops you actually use."
        )


# --------------------------------------------------------------------------- #
# 5. Data
# --------------------------------------------------------------------------- #

def page_data() -> None:
    theme.section("Take your data with you", "CSV, no lock-in")
    frame = data.export_frame()
    if frame.empty:
        theme.empty("Nothing to export yet.")
    else:
        st.download_button(
            "Download price history (CSV)",
            frame.to_csv(index=False).encode("utf-8"),
            file_name="inflationlens-history.csv",
            mime="text/csv",
        )
        theme.note(f"{len(frame)} verified line items.")

    if data.is_demo():
        theme.section("Your workspace", "seeded, private, resettable")
        theme.note(
            f"You are <b>{theme.esc(data.visitor_label())}</b>. The sample basket was copied "
            "for this workspace, so the receipts you add never appear for another visitor."
            " Keep the <code>?u=…</code> in the address bar and your basket is still here "
            "when you return."
        )
        if st.button("Reset my workspace", key="reset_demo"):
            data.reset_demo()
            flash("Workspace reset.", "Back to the seeded sample basket.")
            st.rerun()
    else:
        theme.section("Seeded basket", "optional")
        theme.note("Load nine months of sample receipts into SQLite to explore the app.")
        if st.button("Seed the database", key="seed_db"):
            try:
                created = data.seed_local_database()
                flash("Database seeded.", f"{created} receipts added.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    theme.section("Official CPI", "import or fetch")
    country = st.selectbox(
        "Country", list(SUPPORTED_COUNTRIES),
        index=list(SUPPORTED_COUNTRIES).index(current_country()),
        format_func=lambda code: SUPPORTED_COUNTRIES[code]["label"],
        key="data_country",
    )
    st.session_state["country"] = country

    if data.is_demo():
        theme.note(
            "Imports write to the shared database, so they are disabled in demo mode. "
            "Set <code>PUBLIC_DEMO=false</code> in <code>.env</code> for a private instance."
        )
    else:
        csv_file = st.file_uploader(
            "CPI CSV (period, index_value, optional category / series_id / source)",
            type=["csv"], key="cpi_csv",
        )
        if csv_file is not None:
            try:
                preview = pd.read_csv(csv_file)
                st.dataframe(preview.head(6), hide_index=True, use_container_width=True)
                if st.button("Import these rows", key="cpi_import"):
                    rows = parse_cpi_csv(preview, country)
                    count = data.import_cpi_rows(country, rows)
                    flash("CPI imported.", f"{count} observations stored.")
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not read that CSV: {exc}")

        with st.expander("Fetch from the BLS API (United States)"):
            with st.form("bls_form"):
                series = st.multiselect(
                    "Series", list(BLS_SERIES),
                    default=["CUUR0000SA0", "CUUR0000SAF1"],
                    format_func=lambda key: f"{BLS_SERIES[key]} ({key})",
                )
                years_back = st.slider("Years back", 1, 5, 2)
                submitted = st.form_submit_button("Fetch")
            if submitted:
                try:
                    rows = fetch_bls(
                        series, date.today().year - years_back, date.today().year
                    )
                    count = data.import_cpi_rows("US", rows, source_type="api")
                    flash("CPI fetched.", f"{count} observations stored.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"BLS request failed: {exc}")
            theme.note("A free BLS key raises the daily limit; set <code>BLS_API_KEY</code> in <code>.env</code>.")

    theme.section("This installation", "diagnostics")
    from ui.system_status import render_system_status

    with st.expander("System status"):
        render_system_status()


PAGE_LABELS = {
    "overview": "This month",
    "scan": "Add a receipt",
    "basket": "My basket",
    "cpi": "vs. CPI",
    "data": "Data",
}

PAGES = {
    "overview": page_overview,
    "scan": page_scan,
    "basket": page_basket,
    "cpi": page_cpi,
    "data": page_data,
}
