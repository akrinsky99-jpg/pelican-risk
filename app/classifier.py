# app/classifier.py
#
# This is the brain of the NAICS classifier.
# It takes a business name and address as input
# and returns the most likely NAICS code and industry
# description as output.
#
# MVP approach: keyword matching against a curated
# dictionary of Louisiana business types mapped to
# their correct NAICS codes. No machine learning yet.
# Simple, fast, and demonstrable — exactly right for
# a competition MVP.
#
# Accuracy improves over time by adding more entries
# to the NAICS_MAPPINGS dictionary below.

import re


# ── NAICS MAPPINGS ────────────────────────────────────────────
# This dictionary is the core intellectual asset of the product.
# Each entry maps a list of keywords commonly found in Louisiana
# business names to the correct 6-digit NAICS code and industry
# description.
#
# Structure:
# "keyword": {
#     "code": "6-digit NAICS code",
#     "description": "Official NAICS industry description",
#     "sector": "Broad industry sector name"
# }
#
# Keywords are checked against the business name in order.
# More specific keywords should come before generic ones.
# Example: "oil field services" before "services" so a
# specific match beats a generic one.

NAICS_MAPPINGS = {

    # ── ENERGY AND OIL & GAS ──────────────────────────────────
    # Louisiana's dominant industry — needs strong coverage
    "oilfield": {
        "code": "213112",
        "description": "Support Activities for Oil and Gas Operations",
        "sector": "Mining, Quarrying, and Oil and Gas Extraction"
    },
    "oil field": {
        "code": "213112",
        "description": "Support Activities for Oil and Gas Operations",
        "sector": "Mining, Quarrying, and Oil and Gas Extraction"
    },
    "drilling": {
        "code": "213111",
        "description": "Drilling Oil and Gas Wells",
        "sector": "Mining, Quarrying, and Oil and Gas Extraction"
    },
    "pipeline": {
        "code": "486110",
        "description": "Pipeline Transportation of Crude Oil",
        "sector": "Transportation and Warehousing"
    },
    "refinery": {
        "code": "324110",
        "description": "Petroleum Refineries",
        "sector": "Manufacturing"
    },
    "petroleum": {
        "code": "324110",
        "description": "Petroleum Refineries",
        "sector": "Manufacturing"
    },
    "offshore": {
        "code": "213112",
        "description": "Support Activities for Oil and Gas Operations",
        "sector": "Mining, Quarrying, and Oil and Gas Extraction"
    },
    "energy": {
        "code": "221118",
        "description": "Other Electric Power Generation",
        "sector": "Utilities"
    },

    # ── MARINE AND PORT ───────────────────────────────────────
    # Louisiana has one of the busiest port systems in the US
    "marine": {
        "code": "483211",
        "description": "Inland Water Freight Transportation",
        "sector": "Transportation and Warehousing"
    },
    "maritime": {
        "code": "483211",
        "description": "Inland Water Freight Transportation",
        "sector": "Transportation and Warehousing"
    },
    "offshore marine": {
        "code": "483113",
        "description": "Coastal and Great Lakes Freight Transportation",
        "sector": "Transportation and Warehousing"
    },
    "tugboat": {
        "code": "483211",
        "description": "Inland Water Freight Transportation",
        "sector": "Transportation and Warehousing"
    },
    "barge": {
        "code": "483211",
        "description": "Inland Water Freight Transportation",
        "sector": "Transportation and Warehousing"
    },
    "shipping": {
        "code": "483113",
        "description": "Coastal and Great Lakes Freight Transportation",
        "sector": "Transportation and Warehousing"
    },
    "port": {
        "code": "488310",
        "description": "Port and Harbor Operations",
        "sector": "Transportation and Warehousing"
    },
    "vessel": {
        "code": "483211",
        "description": "Inland Water Freight Transportation",
        "sector": "Transportation and Warehousing"
    },

    # ── CONSTRUCTION ──────────────────────────────────────────
    "construction": {
        "code": "236220",
        "description": "Commercial and Institutional Building Construction",
        "sector": "Construction"
    },
    "contractor": {
        "code": "238990",
        "description": "All Other Specialty Trade Contractors",
        "sector": "Construction"
    },
    "electrical": {
        "code": "238210",
        "description": "Electrical Contractors and Other Wiring Installation",
        "sector": "Construction"
    },
    "plumbing": {
        "code": "238220",
        "description": "Plumbing, Heating, and Air-Conditioning Contractors",
        "sector": "Construction"
    },
    "hvac": {
        "code": "238220",
        "description": "Plumbing, Heating, and Air-Conditioning Contractors",
        "sector": "Construction"
    },
    "roofing": {
        "code": "238160",
        "description": "Roofing Contractors",
        "sector": "Construction"
    },
    "excavation": {
        "code": "238910",
        "description": "Site Preparation Contractors",
        "sector": "Construction"
    },
    "concrete": {
        "code": "238110",
        "description": "Poured Concrete Foundation and Structure Contractors",
        "sector": "Construction"
    },

    # ── FOOD AND RESTAURANT ───────────────────────────────────
    # Louisiana food culture is massive — seafood especially
    "restaurant": {
        "code": "722511",
        "description": "Full-Service Restaurants",
        "sector": "Accommodation and Food Services"
    },
    "cafe": {
        "code": "722515",
        "description": "Snack and Nonalcoholic Beverage Bars",
        "sector": "Accommodation and Food Services"
    },
    "catering": {
        "code": "722320",
        "description": "Caterers",
        "sector": "Accommodation and Food Services"
    },
    "seafood": {
        "code": "722511",
        "description": "Full-Service Restaurants",
        "sector": "Accommodation and Food Services"
    },
    "crawfish": {
        "code": "114112",
        "description": "Shellfish Fishing",
        "sector": "Agriculture, Forestry, Fishing and Hunting"
    },
    "oyster": {
        "code": "114112",
        "description": "Shellfish Fishing",
        "sector": "Agriculture, Forestry, Fishing and Hunting"
    },
    "bar": {
        "code": "722410",
        "description": "Drinking Places (Alcoholic Beverages)",
        "sector": "Accommodation and Food Services"
    },
    "brewery": {
        "code": "312120",
        "description": "Breweries",
        "sector": "Manufacturing"
    },
    "bakery": {
        "code": "311811",
        "description": "Retail Bakeries",
        "sector": "Retail Trade"
    },

    # ── HEALTHCARE ────────────────────────────────────────────
    "hospital": {
        "code": "622110",
        "description": "General Medical and Surgical Hospitals",
        "sector": "Health Care and Social Assistance"
    },
    "clinic": {
        "code": "621111",
        "description": "Offices of Physicians",
        "sector": "Health Care and Social Assistance"
    },
    "pharmacy": {
        "code": "446110",
        "description": "Pharmacies and Drug Stores",
        "sector": "Retail Trade"
    },
    "dental": {
        "code": "621210",
        "description": "Offices of Dentists",
        "sector": "Health Care and Social Assistance"
    },
    "medical": {
        "code": "621111",
        "description": "Offices of Physicians",
        "sector": "Health Care and Social Assistance"
    },
    "nursing": {
        "code": "623110",
        "description": "Nursing Care Facilities",
        "sector": "Health Care and Social Assistance"
    },
    "therapy": {
        "code": "621340",
        "description": "Offices of Physical, Occupational and Speech Therapists",
        "sector": "Health Care and Social Assistance"
    },

    # ── FINANCIAL SERVICES ────────────────────────────────────
    "bank": {
        "code": "522110",
        "description": "Commercial Banking",
        "sector": "Finance and Insurance"
    },
    "credit union": {
        "code": "522130",
        "description": "Credit Unions",
        "sector": "Finance and Insurance"
    },
    "insurance": {
        "code": "524210",
        "description": "Insurance Agencies and Brokerages",
        "sector": "Finance and Insurance"
    },
    "mortgage": {
        "code": "522310",
        "description": "Mortgage and Nonmortgage Loan Brokers",
        "sector": "Finance and Insurance"
    },
    "accounting": {
        "code": "541211",
        "description": "Offices of Certified Public Accountants",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "cpa": {
        "code": "541211",
        "description": "Offices of Certified Public Accountants",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "investment": {
        "code": "523110",
        "description": "Investment Banking and Securities Dealing",
        "sector": "Finance and Insurance"
    },

    # ── REAL ESTATE ───────────────────────────────────────────
    "real estate": {
        "code": "531210",
        "description": "Offices of Real Estate Agents and Brokers",
        "sector": "Real Estate and Rental and Leasing"
    },
    "realty": {
        "code": "531210",
        "description": "Offices of Real Estate Agents and Brokers",
        "sector": "Real Estate and Rental and Leasing"
    },
    "property management": {
        "code": "531311",
        "description": "Residential Property Managers",
        "sector": "Real Estate and Rental and Leasing"
    },
    "appraisal": {
        "code": "531320",
        "description": "Offices of Real Estate Appraisers",
        "sector": "Real Estate and Rental and Leasing"
    },
    "title": {
        "code": "541191",
        "description": "Title Abstract and Settlement Offices",
        "sector": "Professional, Scientific, and Technical Services"
    },

    # ── PROFESSIONAL SERVICES ─────────────────────────────────
    "law": {
        "code": "541110",
        "description": "Offices of Lawyers",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "attorney": {
        "code": "541110",
        "description": "Offices of Lawyers",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "legal": {
        "code": "541110",
        "description": "Offices of Lawyers",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "engineering": {
        "code": "541330",
        "description": "Engineering Services",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "architect": {
        "code": "541310",
        "description": "Architectural Services",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "consulting": {
        "code": "541610",
        "description": "Management Consulting Services",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "staffing": {
        "code": "561320",
        "description": "Temporary Help Services",
        "sector": "Administrative and Support Services"
    },
    "technology": {
        "code": "541512",
        "description": "Computer Systems Design Services",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "software": {
        "code": "511210",
        "description": "Software Publishers",
        "sector": "Information"
    },
    "it services": {
        "code": "541512",
        "description": "Computer Systems Design Services",
        "sector": "Professional, Scientific, and Technical Services"
    },

    # ── RETAIL ────────────────────────────────────────────────
    "grocery": {
        "code": "445110",
        "description": "Supermarkets and Other Grocery Retailers",
        "sector": "Retail Trade"
    },
    "auto": {
        "code": "441110",
        "description": "New Car Dealers",
        "sector": "Retail Trade"
    },
    "hardware": {
        "code": "444110",
        "description": "Home Centers",
        "sector": "Retail Trade"
    },
    "gas station": {
        "code": "447110",
        "description": "Gasoline Stations with Convenience Stores",
        "sector": "Retail Trade"
    },
    "convenience": {
        "code": "445131",
        "description": "Convenience Retailers",
        "sector": "Retail Trade"
    },

    # ── LOGISTICS AND TRANSPORTATION ──────────────────────────
    "trucking": {
        "code": "484110",
        "description": "General Freight Trucking, Local",
        "sector": "Transportation and Warehousing"
    },
    "logistics": {
        "code": "541614",
        "description": "Process, Physical Distribution, and Logistics Consulting",
        "sector": "Professional, Scientific, and Technical Services"
    },
    "warehouse": {
        "code": "493110",
        "description": "General Warehousing and Storage",
        "sector": "Transportation and Warehousing"
    },
    "freight": {
        "code": "484110",
        "description": "General Freight Trucking, Local",
        "sector": "Transportation and Warehousing"
    },

    # ── HOSPITALITY ───────────────────────────────────────────
    "hotel": {
        "code": "721110",
        "description": "Hotels and Motels",
        "sector": "Accommodation and Food Services"
    },
    "motel": {
        "code": "721110",
        "description": "Hotels and Motels",
        "sector": "Accommodation and Food Services"
    },
    "inn": {
        "code": "721110",
        "description": "Hotels and Motels",
        "sector": "Accommodation and Food Services"
    },

    # ── AGRICULTURE ───────────────────────────────────────────
    # Louisiana has significant agricultural output
    "farming": {
        "code": "111998",
        "description": "All Other Miscellaneous Crop Farming",
        "sector": "Agriculture, Forestry, Fishing and Hunting"
    },
    "sugarcane": {
        "code": "111930",
        "description": "Sugarcane Farming",
        "sector": "Agriculture, Forestry, Fishing and Hunting"
    },
    "timber": {
        "code": "113110",
        "description": "Timber Tract Operations",
        "sector": "Agriculture, Forestry, Fishing and Hunting"
    },
    "forestry": {
        "code": "113110",
        "description": "Timber Tract Operations",
        "sector": "Agriculture, Forestry, Fishing and Hunting"
    },

    # ── EDUCATION ─────────────────────────────────────────────
    "school": {
        "code": "611110",
        "description": "Elementary and Secondary Schools",
        "sector": "Educational Services"
    },
    "university": {
        "code": "611310",
        "description": "Colleges, Universities, and Professional Schools",
        "sector": "Educational Services"
    },
    "tutoring": {
        "code": "611691",
        "description": "Exam Preparation and Tutoring",
        "sector": "Educational Services"
    },
    "daycare": {
        "code": "624410",
        "description": "Child Care Services",
        "sector": "Health Care and Social Assistance"
    },

    # ── MANUFACTURING ─────────────────────────────────────────
    "manufacturing": {
        "code": "339999",
        "description": "All Other Miscellaneous Manufacturing",
        "sector": "Manufacturing"
    },
    "fabrication": {
        "code": "332312",
        "description": "Fabricated Structural Metal Manufacturing",
        "sector": "Manufacturing"
    },
    "chemical": {
        "code": "325199",
        "description": "All Other Basic Organic Chemical Manufacturing",
        "sector": "Manufacturing"
    },
    "plant": {
        "code": "325199",
        "description": "All Other Basic Organic Chemical Manufacturing",
        "sector": "Manufacturing"
    },

    # ── PERSONAL SERVICES ─────────────────────────────────────
    "salon": {
        "code": "812112",
        "description": "Beauty Salons",
        "sector": "Other Services"
    },
    "barber": {
        "code": "812111",
        "description": "Barber Shops",
        "sector": "Other Services"
    },
    "funeral": {
        "code": "812210",
        "description": "Funeral Homes and Funeral Services",
        "sector": "Other Services"
    },
    "laundry": {
        "code": "812310",
        "description": "Coin-Operated Laundries and Drycleaners",
        "sector": "Other Services"
    },
    "cleaning": {
        "code": "561720",
        "description": "Janitorial Services",
        "sector": "Administrative and Support Services"
    },
    "landscaping": {
        "code": "561730",
        "description": "Landscaping Services",
        "sector": "Administrative and Support Services"
    },
    "security": {
        "code": "561612",
        "description": "Security Guards and Patrol Services",
        "sector": "Administrative and Support Services"
    },
}


# ── CLASSIFIER FUNCTIONS ──────────────────────────────────────

def normalize(text):
    """
    Cleans and standardizes input text before matching.
    Converts to lowercase and removes punctuation so that
    'Oil-Field Services LLC' matches 'oilfield' correctly.
    """
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation and special characters
    # re.sub replaces anything that isn't a letter,
    # number, or space with an empty string
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def classify_by_keywords(business_name):
    """
    Scans the business name for known keywords and returns
    the best matching NAICS code.

    Uses a two-pass system:
    Pass 1 — checks industry-specific keywords first
    Pass 2 — checks generic keywords second

    This prevents generic words from overriding specific
    industry terms. Oilfield Contractors matches oilfield
    not contractor.
    """
    normalized_name = normalize(business_name)

    # Generic words that should never win over a more
    # specific industry keyword
    GENERIC_KEYWORDS = {
        "contractor", "services", "solutions", "group",
        "company", "enterprises", "industries", "management",
        "associates", "partners", "holdings", "ventures"
    }

    # Pass 1 — specific keywords only
    specific_keywords = sorted(
        [k for k in NAICS_MAPPINGS.keys() if k not in GENERIC_KEYWORDS],
        key=len,
        reverse=True
    )

    for keyword in specific_keywords:
        if keyword in normalized_name:
            match = NAICS_MAPPINGS[keyword]
            return {
                "naics_code": match["code"],
                "description": match["description"],
                "sector": match["sector"],
                "confidence": "high",
                "match_keyword": keyword,
                "method": "keyword_match"
            }

    # Pass 2 — generic keywords as fallback
    generic_keywords = sorted(
        [k for k in NAICS_MAPPINGS.keys() if k in GENERIC_KEYWORDS],
        key=len,
        reverse=True
    )

    for keyword in generic_keywords:
        if keyword in normalized_name:
            match = NAICS_MAPPINGS[keyword]
            return {
                "naics_code": match["code"],
                "description": match["description"],
                "sector": match["sector"],
                "confidence": "medium",
                "match_keyword": keyword,
                "method": "generic_keyword_match"
            }

    return None


def classify_business(business_name, address=None):
    """
    Main classification function — the one the API calls.

    Takes a business name and optional address as input.
    Returns a structured classification result.

    Current logic:
    1. Try keyword matching against business name
    2. If no match, return unclassified result

    Future improvements (post-MVP):
    - Louisiana SOS database lookup
    - Machine learning classifier
    - Website content analysis
    """

    # Guard against empty input
    if not business_name or not business_name.strip():
        return {
            "success": False,
            "error": "Business name is required",
            "business_name": business_name,
            "address": address
        }

    # Attempt keyword classification
    result = classify_by_keywords(business_name)

    if result:
        # Successfully classified
        return {
            "success": True,
            "business_name": business_name,
            "address": address,
            "naics_code": result["naics_code"],
            "description": result["description"],
            "sector": result["sector"],
            "confidence": result["confidence"],
            "match_keyword": result["match_keyword"],
            "method": result["method"]
        }
    else:
        # Could not classify — return honest unclassified result
        # rather than guessing wrong
        return {
            "success": False,
            "business_name": business_name,
            "address": address,
            "naics_code": None,
            "description": "Could not classify this business",
            "sector": None,
            "confidence": "none",
            "match_keyword": None,
            "method": "no_match",
            "suggestion": "Add this business type to NAICS_MAPPINGS in classifier.py"
        }


def test_classifier():
    """
    Quick sanity check — run a handful of Louisiana
    business names through the classifier and print
    the results so you can verify it's working correctly.

    Run this directly with: python app/classifier.py
    """
    test_businesses = [
        ("Offshore Energy Services LLC", "Lafayette, LA"),
        ("Baton Rouge Crawfish Co", "Baton Rouge, LA"),
        ("Gulf Coast Trucking", "New Orleans, LA"),
        ("Johnson Law Firm", "Baton Rouge, LA"),
        ("Pelican State Credit Union", "Baton Rouge, LA"),
        ("Acadian Oilfield Contractors", "Lafayette, LA"),
        ("New Orleans Roofing Solutions", "New Orleans, LA"),
        ("XYZ Mystery Company", "Shreveport, LA"),
    ]

    print("=" * 60)
    print("NAICS CLASSIFIER — TEST RESULTS")
    print("=" * 60)

    correct = 0
    unclassified = 0

    for name, address in test_businesses:
        result = classify_business(name, address)
        status = "✅" if result["success"] else "❌"
        print(f"\n{status} {name}")
        print(f"   Address:     {address}")
        if result["success"]:
            print(f"   NAICS Code:  {result['naics_code']}")
            print(f"   Industry:    {result['description']}")
            print(f"   Sector:      {result['sector']}")
            print(f"   Confidence:  {result['confidence']}")
            print(f"   Matched on:  '{result['match_keyword']}'")
            correct += 1
        else:
            print(f"   Result:      {result['description']}")
            unclassified += 1

    print("\n" + "=" * 60)
    print(f"Results: {correct} classified, {unclassified} unclassified")
    print(f"Accuracy: {round(correct/len(test_businesses)*100)}%")
    print("=" * 60)


# Run test_classifier() when this file is executed directly
# This won't run when classifier.py is imported by main.py
if __name__ == "__main__":
    test_classifier()
