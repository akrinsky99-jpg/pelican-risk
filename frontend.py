# frontend.py — Pelican Risk
# Streamlit UI with four tabs:
# 1. Classify    — single business lookup
# 2. Batch       — CSV upload and results
# 3. Review Queue — flagged classifications for human review
# 4. Portfolio   — concentration dashboard

import streamlit as st
import requests
import pandas as pd
import json

# ── CONFIG ────────────────────────────────────────────────────
# The API runs locally alongside this frontend.
# In production this would be an environment variable.

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Pelican Risk",
    page_icon="🦩",
    layout="wide"
)

# ── SIDEBAR ───────────────────────────────────────────────────
# API key input so any institution can log in with their key.

st.sidebar.image("https://img.icons8.com/emoji/96/flamingo.png", width=60)
st.sidebar.title("Pelican Risk")
st.sidebar.caption("NAICS Classification & Portfolio Intelligence")
st.sidebar.divider()

api_key = st.sidebar.text_input(
    "API Key",
    value="7b807e70-8f45-4040-8b93-74243e289605",
    type="password"
)

headers = {"x-api-key": api_key, "Content-Type": "application/json"}

# Quick connection check
try:
    r = requests.get(f"{API_URL}/health", timeout=3)
    if r.status_code == 200:
        st.sidebar.success("API connected")
    else:
        st.sidebar.error("API error")
except Exception:
    st.sidebar.error("Cannot reach API — is uvicorn running?")

st.sidebar.divider()
st.sidebar.caption("Built for Louisiana community banks, credit unions, and insurance agencies.")


# ── HELPERS ───────────────────────────────────────────────────

def confidence_color(tier):
    palette = {"high": "🟢", "medium": "🟡", "low": "🔴", "unclassified": "⚫"}
    return palette.get(tier, "⚫")


def render_export_buttons(classification_id: str, key_prefix: str):
    """Render PDF and Excel download buttons for a classification's audit trail."""
    col1, col2 = st.columns(2)
    with col1:
        resp = requests.get(
            f"{API_URL}/audit/{classification_id}/export",
            headers={k: v for k, v in headers.items() if k != "Content-Type"},
            params={"format": "pdf"},
        )
        if resp.status_code == 200:
            st.download_button(
                "Download PDF",
                data=resp.content,
                file_name=f"audit_{classification_id[:8]}.pdf",
                mime="application/pdf",
                key=f"{key_prefix}_pdf_{classification_id}",
            )
    with col2:
        resp = requests.get(
            f"{API_URL}/audit/{classification_id}/export",
            headers={k: v for k, v in headers.items() if k != "Content-Type"},
            params={"format": "excel"},
        )
        if resp.status_code == 200:
            st.download_button(
                "Download Excel",
                data=resp.content,
                file_name=f"audit_{classification_id[:8]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_prefix}_xl_{classification_id}",
            )

def classify_one(business_name, address):
    """Calls POST /classify and returns the result dict."""
    r = requests.post(
        f"{API_URL}/classify",
        headers=headers,
        json={"business_name": business_name, "address": address}
    )
    return r.json()

def get_history(needs_review=None, limit=100):
    """Calls GET /history with optional needs_review filter."""
    params = {"limit": limit}
    if needs_review is not None:
        params["needs_review"] = needs_review
    r = requests.get(f"{API_URL}/history", headers=headers, params=params)
    return r.json()

def confirm(classification_id, confirmed_by="reviewer"):
    """Calls PUT /classifications/{id}/confirm"""
    r = requests.put(
        f"{API_URL}/classifications/{classification_id}/confirm",
        headers=headers,
        json={"confirmed_by": confirmed_by}
    )
    return r.json()

def correct(classification_id, corrected_code, reason, corrected_by="reviewer"):
    """Calls PUT /classifications/{id}/correct"""
    r = requests.put(
        f"{API_URL}/classifications/{classification_id}/correct",
        headers=headers,
        json={
            "corrected_naics_code": corrected_code,
            "correction_reason": reason,
            "corrected_by": corrected_by
        }
    )
    return r.json()

def get_portfolio():
    """Calls GET /portfolio/concentration"""
    r = requests.get(f"{API_URL}/portfolio/concentration", headers=headers)
    return r.json()


# ── TABS ──────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Classify",
    "📂 Batch Upload",
    "📋 Review Queue",
    "📊 Portfolio",
    "🗂️ History"
])


# ══════════════════════════════════════════════════════════════
# TAB 1 — CLASSIFY
# Single business lookup with full result display
# ══════════════════════════════════════════════════════════════

with tab1:
    st.header("Classify a Business")
    st.caption("Enter a business name and address to get a NAICS code, confidence score, and audit-ready reasoning.")

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business Name", placeholder="e.g. Gulf Coast Oilfield Services LLC")
    with col2:
        address = st.text_input("Address (optional)", placeholder="e.g. Lafayette, LA")

    if st.button("Classify", type="primary"):
        if not business_name:
            st.warning("Enter a business name.")
        else:
            with st.spinner("Classifying..."):
                result = classify_one(business_name, address)

            if result.get("success"):
                # Main result row
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("NAICS Code", result["naics_code"])
                c2.metric("Confidence", f"{result['confidence_score']}")
                c3.metric("Tier", f"{confidence_color(result['confidence_tier'])} {result['confidence_tier'].upper()}")
                c4.metric("Review Required", "Yes" if result["needs_review"] else "No")

                st.divider()

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Industry:** {result['naics_description']}")
                    st.markdown(f"**Sector:** {result['naics_sector']}")
                    if result.get("parish"):
                        st.markdown(f"**Parish:** {result['parish']}")
                with col_b:
                    st.markdown(f"**Matched keyword:** `{result.get('match_keyword', 'none')}`")
                    st.markdown(f"**Keywords matched:** {result.get('match_count', 0)}")
                    st.markdown(f"**Conflict detected:** {'⚠️ Yes' if result.get('conflict_detected') else 'No'}")

                st.divider()
                st.markdown("**Audit Reasoning:**")
                st.info(result.get("reasoning", "No reasoning available."))

                if result["needs_review"]:
                    st.warning("⚠️ This classification has been flagged for human review. Go to the Review Queue tab to confirm or correct it.")

            else:
                st.error(f"Could not classify: {result.get('naics_description', 'Unknown error')}")
                st.info("This business has been added to the Review Queue for manual classification.")


# ══════════════════════════════════════════════════════════════
# TAB 2 — BATCH UPLOAD
# CSV upload — classifies all rows and shows results table
# ══════════════════════════════════════════════════════════════

with tab2:
    st.header("Batch Upload")
    st.caption("Upload a CSV with your business names to classify your entire portfolio at once.")

    st.markdown("**Required CSV format:**")
    st.code("business_name,address\nGulf Coast Trucking,New Orleans LA\nPelican State Credit Union,Baton Rouge LA")

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)

        # Validate columns
        if "business_name" not in df.columns:
            st.error("CSV must have a 'business_name' column.")
        else:
            st.write(f"Found **{len(df)} businesses**. Preview:")
            st.dataframe(df.head(), use_container_width=True)

            if st.button("Classify All", type="primary"):
                if len(df) > 500:
                    st.error("Maximum 500 businesses per batch.")
                else:
                    businesses = []
                    for _, row in df.iterrows():
                        businesses.append({
                            "business_name": str(row["business_name"]),
                            "address": str(row.get("address", "")) if pd.notna(row.get("address")) else None
                        })

                    with st.spinner(f"Classifying {len(businesses)} businesses..."):
                        r = requests.post(
                            f"{API_URL}/classify/batch",
                            headers=headers,
                            json={"businesses": businesses}
                        )
                        batch_result = r.json()

                    # Summary metrics
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total", batch_result["total"])
                    c2.metric("Classified", batch_result["classified"])
                    c3.metric("Needs Review", batch_result["needs_review"])
                    c4.metric("Failed", batch_result["failed"])

                    st.divider()

                    # Results table
                    rows = []
                    for r in batch_result["results"]:
                        rows.append({
                            "Business": r.get("business_name"),
                            "NAICS Code": r.get("naics_code") or "—",
                            "Description": r.get("naics_description") or "—",
                            "Score": r.get("confidence_score") or 0,
                            "Tier": r.get("confidence_tier") or "—",
                            "Review?": "⚠️ Yes" if r.get("needs_review") else "✅ No",
                            "Conflict": "⚠️ Yes" if r.get("conflict_detected") else "No",
                        })

                    results_df = pd.DataFrame(rows)
                    st.dataframe(results_df, use_container_width=True)

                    # Download results
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        "Download Results CSV",
                        data=csv,
                        file_name="pelican_risk_results.csv",
                        mime="text/csv"
                    )

                    if batch_result["needs_review"] > 0:
                        st.warning(f"⚠️ {batch_result['needs_review']} classifications need human review. Go to the Review Queue tab.")


# ══════════════════════════════════════════════════════════════
# TAB 3 — REVIEW QUEUE
# Shows all needs_review=true classifications
# Compliance officer can confirm or correct each one
# ══════════════════════════════════════════════════════════════

with tab3:
    st.header("Review Queue")
    st.caption("Classifications flagged for human review. Confirm correct ones or reassign incorrect ones. Every action is permanently recorded.")

    if st.button("Refresh Queue"):
        st.rerun()

    history = get_history(needs_review=True, limit=100)
    items = history.get("results", [])

    if not items:
        st.success("✅ Review queue is empty — all classifications have been reviewed.")
    else:
        st.warning(f"⚠️ {len(items)} classifications awaiting review")
        st.divider()

        for item in items:
            with st.expander(
                f"{confidence_color(item['confidence_tier'])} {item['business_name']} — "
                f"{item.get('naics_code') or 'UNCLASSIFIED'} | Score: {item.get('confidence_score')} | "
                f"{'⚠️ CONFLICT' if item.get('conflict_detected') else ''}",
                expanded=False
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Business:** {item['business_name']}")
                    st.markdown(f"**Address:** {item.get('address') or '—'}")
                    st.markdown(f"**Parish:** {item.get('parish') or '—'}")
                    st.markdown(f"**Current NAICS:** {item.get('naics_code') or '—'}")
                    st.markdown(f"**Description:** {item.get('naics_description') or '—'}")
                with col2:
                    st.markdown(f"**Confidence Score:** {item.get('confidence_score')}")
                    st.markdown(f"**Tier:** {item.get('confidence_tier')}")
                    st.markdown(f"**Method:** {item.get('method')}")
                    st.markdown(f"**Matched keyword:** `{item.get('match_keyword') or 'none'}`")

                st.markdown("**Reasoning:**")
                st.info(item.get("reasoning") or "No reasoning available.")

                st.divider()
                st.markdown("**Action:**")

                action_col1, action_col2 = st.columns(2)

                with action_col1:
                    st.markdown("✅ **Confirm as correct**")
                    reviewer = st.text_input("Your name", value="reviewer", key=f"reviewer_{item['id']}")
                    if st.button("Confirm", key=f"confirm_{item['id']}"):
                        result = confirm(item["id"], confirmed_by=reviewer)
                        if result.get("success"):
                            st.success("Confirmed and locked.")
                            st.rerun()
                        else:
                            st.error("Error confirming.")

                with action_col2:
                    st.markdown("✏️ **Correct to a different code**")
                    new_code = st.text_input("Correct NAICS code", placeholder="e.g. 213112", key=f"code_{item['id']}")
                    reason = st.text_input("Reason for correction", placeholder="e.g. Business is oilfield, not marine", key=f"reason_{item['id']}")
                    if st.button("Submit Correction", key=f"correct_{item['id']}"):
                        if not new_code:
                            st.warning("Enter the correct NAICS code.")
                        else:
                            result = correct(item["id"], new_code, reason, corrected_by=reviewer)
                            if result.get("success"):
                                st.success(f"Corrected to {new_code}.")
                                st.rerun()
                            else:
                                st.error("Error submitting correction.")

                st.divider()
                st.markdown("**Export audit report:**")
                render_export_buttons(item["id"], key_prefix="rq")


# ══════════════════════════════════════════════════════════════
# TAB 4 — PORTFOLIO
# Concentration dashboard — the Chief Risk Officer view
# ══════════════════════════════════════════════════════════════

with tab4:
    st.header("Portfolio Concentration")
    st.caption("Industry breakdown of your classified business portfolio. Sectors above 20% are flagged.")

    if st.button("Refresh Portfolio"):
        st.rerun()

    portfolio = get_portfolio()

    if portfolio.get("total_classified", 0) == 0:
        st.info("No classified businesses yet. Use the Classify or Batch Upload tabs to get started.")
    else:
        # Summary
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Classified", portfolio["total_classified"])
        warnings = sum(1 for s in portfolio["sectors"] if s.get("concentration_warning"))
        c2.metric("Sectors", len(portfolio["sectors"]))
        c3.metric("Concentration Warnings", warnings, delta=f"{warnings} sectors above 20%", delta_color="inverse")

        st.divider()

        # Bar chart
        sectors_df = pd.DataFrame([
            {"Sector": s["sector"], "Percentage": s["percentage"], "Count": s["count"]}
            for s in portfolio["sectors"]
        ])

        st.bar_chart(sectors_df.set_index("Sector")["Percentage"])

        st.divider()

        # Detail table with warnings
        st.markdown("**Sector Breakdown:**")
        for s in portfolio["sectors"]:
            warning = "⚠️ Concentration Warning" if s.get("concentration_warning") else ""
            with st.expander(f"{s['sector']} — {s['percentage']}%  {warning}"):
                st.markdown(f"**Count:** {s['count']} businesses")
                st.markdown(f"**Businesses:** {', '.join(s['businesses'])}")
                if s.get("concentration_warning"):
                    st.warning(f"This sector exceeds the 20% concentration threshold. Consider diversifying or reviewing your exposure.")


# ══════════════════════════════════════════════════════════════
# TAB 5 — HISTORY
# Full searchable, filterable classification log
# ══════════════════════════════════════════════════════════════

with tab5:
    st.header("Classification History")
    st.caption("Browse and search all past classifications. Export to CSV for reporting or examiner requests.")

    # ── FILTERS ───────────────────────────────────────────────
    with st.expander("Filters", expanded=True):
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            search_query = st.text_input("Search business name", placeholder="e.g. Gulf Coast")
        with f2:
            tier_filter = st.selectbox(
                "Confidence tier",
                ["All", "high", "medium", "low", "unclassified"]
            )
        with f3:
            confirmed_filter = st.selectbox(
                "Status",
                ["All", "Confirmed", "Unconfirmed"]
            )
        with f4:
            review_filter = st.selectbox(
                "Review flag",
                ["All", "Needs review", "Reviewed"]
            )
        with f5:
            limit = st.selectbox("Max results", [50, 100, 250, 500], index=1)

    if st.button("Search", type="primary"):
        st.session_state["history_search_triggered"] = True

    # Run query on load and when search button is pressed
    params = {"limit": limit}
    if search_query:
        params["search"] = search_query
    if tier_filter != "All":
        params["confidence_tier"] = tier_filter
    if confirmed_filter == "Confirmed":
        params["confirmed"] = "true"
    elif confirmed_filter == "Unconfirmed":
        params["confirmed"] = "false"
    if review_filter == "Needs review":
        params["needs_review"] = "true"
    elif review_filter == "Reviewed":
        params["needs_review"] = "false"

    r = requests.get(f"{API_URL}/history", headers=headers, params=params)
    hist = r.json()
    items = hist.get("results", [])

    # ── SUMMARY ROW ──────────────────────────────────────────
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Records returned", len(items))
    confirmed_count = sum(1 for i in items if i.get("confirmed"))
    m2.metric("Confirmed", confirmed_count)
    review_count = sum(1 for i in items if i.get("needs_review"))
    m3.metric("Needs review", review_count)
    high_conf = sum(1 for i in items if i.get("confidence_tier") == "high")
    m4.metric("High confidence", high_conf)

    st.divider()

    if not items:
        st.info("No records found. Try adjusting your filters.")
    else:
        # ── TABLE ─────────────────────────────────────────────
        rows = []
        for item in items:
            rows.append({
                "Business": item.get("business_name", ""),
                "NAICS Code": item.get("naics_code") or "—",
                "Description": item.get("naics_description") or "—",
                "Sector": item.get("naics_sector") or "—",
                "Parish": item.get("parish") or "—",
                "Score": item.get("confidence_score", 0),
                "Tier": item.get("confidence_tier", "—"),
                "Confirmed": "✅" if item.get("confirmed") else "—",
                "Needs Review": "⚠️" if item.get("needs_review") else "—",
                "Conflict": "⚠️" if item.get("conflict_detected") else "—",
                "Method": item.get("method", "—"),
                "Date": (item.get("created_at") or "")[:10],
                "ID": item.get("id", ""),
            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )

        # ── EXPORT ────────────────────────────────────────────
        csv = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="pelican_risk_history.csv",
            mime="text/csv"
        )

        # ── RECORD DETAIL ─────────────────────────────────────
        st.divider()
        st.markdown("**Audit detail** — select a record to see full reasoning and corrections:")
        selected_name = st.selectbox(
            "Select a business",
            options=["—"] + [i.get("business_name", "") for i in items],
            index=0
        )

        if selected_name != "—":
            selected = next((i for i in items if i.get("business_name") == selected_name), None)
            if selected:
                c1, c2, c3 = st.columns(3)
                c1.metric("NAICS Code", selected.get("naics_code") or "Unclassified")
                c2.metric("Confidence Score", selected.get("confidence_score", 0))
                c3.metric("Tier", f"{confidence_color(selected.get('confidence_tier', ''))} {(selected.get('confidence_tier') or '').upper()}")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Industry:** {selected.get('naics_description') or '—'}")
                    st.markdown(f"**Sector:** {selected.get('naics_sector') or '—'}")
                    st.markdown(f"**Parish:** {selected.get('parish') or '—'}")
                    st.markdown(f"**Address:** {selected.get('address') or '—'}")
                with col_b:
                    st.markdown(f"**Method:** {selected.get('method') or '—'}")
                    st.markdown(f"**Matched keyword:** `{selected.get('match_keyword') or 'none'}`")
                    st.markdown(f"**Confirmed by:** {selected.get('confirmed_by') or '—'}")
                    st.markdown(f"**Date:** {(selected.get('created_at') or '')[:19].replace('T', ' ')}")

                st.markdown("**Audit Reasoning:**")
                st.info(selected.get("reasoning") or "No reasoning recorded.")

                # Fetch full audit trail from API
                audit_r = requests.get(
                    f"{API_URL}/audit/{selected['id']}",
                    headers=headers
                )
                if audit_r.status_code == 200:
                    audit = audit_r.json()
                    corrections = audit.get("correction_history", [])
                    if corrections:
                        st.markdown(f"**Correction history ({len(corrections)} corrections):**")
                        for c in corrections:
                            st.markdown(
                                f"- `{c['original_code']}` → `{c['corrected_to']}` "
                                f"by **{c['corrected_by']}** on {(c.get('corrected_at') or '')[:10]}"
                                + (f" — *{c['reason']}*" if c.get('reason') else "")
                            )

                st.divider()
                st.markdown("**Export audit report:**")
                render_export_buttons(selected["id"], key_prefix="hist")