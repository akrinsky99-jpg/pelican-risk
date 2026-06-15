# frontend.py
#
# This is the web interface for the Louisiana NAICS Classifier.
# Built with Streamlit — a Python library that turns regular
# Python scripts into interactive web applications.
#
# This file is completely separate from the API (main.py).
# The API serves developers who call it programmatically.
# This interface serves non-technical users — bank loan
# officers, insurance agents, judges, potential customers —
# who just want to type a name and see a result.
#
# Run with: streamlit run frontend.py

import streamlit as st
import requests
import json

# ── PAGE CONFIGURATION ────────────────────────────────────────
# Must be the first Streamlit command in the file.
# Sets the browser tab title, icon, and layout width.
st.set_page_config(
    page_title="Louisiana NAICS Classifier",
    page_icon="🦅",
    layout="centered"
)

# ── API CONNECTION ─────────────────────────────────────────────
# The frontend talks to the API we built in main.py.
# When running locally both are on the same machine so
# we use localhost. In production this would be the
# deployed API URL.
API_URL = "http://127.0.0.1:8000"


# ── HELPER FUNCTIONS ──────────────────────────────────────────

def classify_single(business_name, address):
    """
    Sends a single classification request to the API
    and returns the response as a Python dictionary.
    Returns None if the API call fails.
    """
    try:
        response = requests.post(
            f"{API_URL}/classify",
            json={
                "business_name": business_name,
                "address": address
            },
            # Timeout after 5 seconds so the UI doesn't
            # hang forever if the API is unresponsive
            timeout=5
        )
        return response.json()
    except Exception as e:
        return None


def classify_batch_from_text(raw_text):
    """
    Takes raw text with one business per line and
    converts it into a batch classification request.
    
    Example input:
    Gulf Coast Trucking, New Orleans LA
    Johnson Law Firm, Baton Rouge LA
    Pelican State Credit Union, Baton Rouge LA
    
    Splits each line on the last comma to separate
    business name from address.
    """
    businesses = []
    for line in raw_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # Split on last comma to separate name from address
        # "Gulf Coast Trucking, New Orleans LA" becomes
        # name="Gulf Coast Trucking" address="New Orleans LA"
        if ',' in line:
            parts = line.rsplit(',', 1)
            businesses.append({
                "business_name": parts[0].strip(),
                "address": parts[1].strip()
            })
        else:
            # No comma — treat whole line as business name
            businesses.append({
                "business_name": line,
                "address": None
            })
    return businesses


# ── PAGE HEADER ───────────────────────────────────────────────
st.title("🦅 Louisiana NAICS Classifier")
st.markdown("""
**Instantly classify Louisiana businesses by industry code.**

Built for community banks, credit unions, and insurance agencies 
who need fast, accurate NAICS classification without enterprise pricing.


""")

# Visual divider between header and main content
st.divider()


# ── TAB LAYOUT ────────────────────────────────────────────────
# Tabs let us offer both single and batch classification
# in one clean interface without cluttering the page.
tab1, tab2, tab3 = st.tabs([
    "🔍 Single Lookup",
    "📋 Batch Classification",
    "📊 Coverage"
])


# ── TAB 1: SINGLE LOOKUP ──────────────────────────────────────
with tab1:
    st.subheader("Classify a Business")
    st.markdown("Enter a business name and address to get the NAICS industry code.")

    # Input fields
    business_name = st.text_input(
        "Business Name",
        placeholder="e.g. Gulf Coast Oilfield Services LLC",
        help="Enter the full legal business name for best results"
    )

    address = st.text_input(
        "Address (optional)",
        placeholder="e.g. Lafayette, LA 70501",
        help="Adding an address improves classification accuracy"
    )

    # Classify button
    if st.button("Classify", type="primary", use_container_width=True):

        # Validate input before calling API
        if not business_name.strip():
            st.error("Please enter a business name.")
        else:
            # Show spinner while waiting for API response
            with st.spinner("Classifying..."):
                result = classify_single(business_name, address)

            if result is None:
                # API call failed entirely
                st.error("Could not connect to the classifier. Make sure the API is running.")

            elif result.get("success"):
                # Successfully classified — show results
                st.success("Classification successful")

                # Main result displayed prominently
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        label="NAICS Code",
                        value=result["naics_code"]
                    )
                with col2:
                    st.metric(
                        label="Confidence",
                        value=result["confidence"].upper()
                    )

                # Industry details
                st.markdown(f"**Industry:** {result['description']}")
                st.markdown(f"**Sector:** {result['sector']}")

                # Technical details in an expander
                # so they don't clutter the main view
                # but are available for curious users
                with st.expander("Technical Details"):
                    st.markdown(f"**Match Method:** {result['method']}")
                    st.markdown(f"**Matched Keyword:** `{result['match_keyword']}`")
                    st.markdown(f"**Business Name:** {result['business_name']}")
                    st.markdown(f"**Address:** {result['address'] or 'Not provided'}")

                    # Show the raw JSON response for
                    # developers who want to see the full output
                    st.markdown("**Raw API Response:**")
                    st.json(result)

            else:
                # API responded but couldn't classify
                st.warning("Could not classify this business automatically.")
                st.markdown("""
                **What this means:**
                - The business name doesn't contain recognizable industry keywords
                - Try adding more descriptive words to the business name
                - Example: instead of "Johnson LLC" try "Johnson Electrical Contractors"
                
                **This business has been flagged for manual review.**
                """)

                with st.expander("Technical Details"):
                    st.json(result)

    # Example businesses users can click to try
    st.divider()
    st.markdown("**Try these Louisiana examples:**")

    # Create a row of example buttons
    examples = [
        ("Pelican State Credit Union", "Baton Rouge, LA"),
        ("Acadian Oilfield Contractors", "Lafayette, LA"),
        ("Gulf Coast Trucking", "New Orleans, LA"),
        ("Johnson Law Firm", "Baton Rouge, LA"),
    ]

    # Display examples in a 2x2 grid
    col1, col2 = st.columns(2)
    for i, (name, addr) in enumerate(examples):
        col = col1 if i % 2 == 0 else col2
        with col:
            if st.button(f"{name}", key=f"example_{i}", use_container_width=True):
                with st.spinner("Classifying..."):
                    result = classify_single(name, addr)
                if result and result.get("success"):
                    st.success(f"**{result['naics_code']}** — {result['description']}")
                    st.caption(f"Sector: {result['sector']} | Confidence: {result['confidence']}")


# ── TAB 2: BATCH CLASSIFICATION ───────────────────────────────
with tab2:
    st.subheader("Batch Classification")
    st.markdown("""
    Classify multiple businesses at once.
    Enter one business per line in the format:
    `Business Name, City State`
    """)

    # Default example text to show users the expected format
    default_batch = """Gulf Coast Trucking, New Orleans LA
Johnson Law Firm, Baton Rouge LA
Pelican State Credit Union, Baton Rouge LA
Acadian Oilfield Contractors, Lafayette LA
New Orleans Roofing Solutions, New Orleans LA
XYZ Mystery Company, Shreveport LA"""

    batch_input = st.text_area(
        "Enter businesses (one per line)",
        value=default_batch,
        height=200,
        help="Format: Business Name, City State"
    )

    if st.button("Classify All", type="primary", use_container_width=True):

        businesses = classify_batch_from_text(batch_input)

        if not businesses:
            st.error("No valid businesses found. Check your input format.")
        else:
            with st.spinner(f"Classifying {len(businesses)} businesses..."):
                try:
                    response = requests.post(
                        f"{API_URL}/classify/batch",
                        json=businesses,
                        timeout=30
                    )
                    batch_result = response.json()
                except Exception as e:
                    st.error(f"API connection failed: {e}")
                    batch_result = None

            if batch_result:
                # Summary metrics at the top
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", batch_result["total"])
                with col2:
                    st.metric("Classified", batch_result["classified"])
                with col3:
                    st.metric(
                        "Accuracy",
                        f"{batch_result['accuracy_rate']}%"
                    )

                st.divider()

                # Individual results
                for result in batch_result["results"]:
                    if result["success"]:
                        # Green success box for classified businesses
                        with st.container():
                            col1, col2, col3 = st.columns([3, 1, 2])
                            with col1:
                                st.markdown(f"**{result['business_name']}**")
                                st.caption(result.get('address', ''))
                            with col2:
                                st.markdown(f"`{result['naics_code']}`")
                            with col3:
                                st.markdown(result['description'])
                    else:
                        # Gray unclassified box
                        with st.container():
                            col1, col2 = st.columns([3, 3])
                            with col1:
                                st.markdown(f"~~{result['business_name']}~~")
                            with col2:
                                st.caption("⚠️ Could not classify")

                # Download results as JSON
                st.divider()
                st.download_button(
                    label="Download Results as JSON",
                    data=json.dumps(batch_result, indent=2),
                    file_name="naics_classification_results.json",
                    mime="application/json"
                )


# ── TAB 3: COVERAGE ───────────────────────────────────────────
with tab3:
    st.subheader("Industry Coverage")
    st.markdown("Industries and keywords the classifier currently recognizes.")

    with st.spinner("Loading coverage data..."):
        try:
            response = requests.get(f"{API_URL}/coverage", timeout=5)
            coverage = response.json()
        except Exception:
            coverage = None

    if coverage:
        # Top level metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Keywords", coverage["total_keywords"])
        with col2:
            st.metric("Industry Sectors", coverage["total_sectors"])

        st.divider()

        # Each sector as an expander
        for sector in coverage["sectors"]:
            with st.expander(
                f"**{sector['sector']}** — {sector['keyword_count']} keywords"
            ):
                # Display keywords as a comma separated list
                st.markdown(
                    ", ".join([f"`{k}`" for k in sector["keywords"]])
                )
    else:
        st.error("Could not load coverage data. Make sure the API is running.")


# ── FOOTER ────────────────────────────────────────────────────
st.divider()
st.caption(
    "Project Pelican · Louisiana NAICS Classifier · "
    ""
    "Built with FastAPI and Streamlit"
)