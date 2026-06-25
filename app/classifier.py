# app/classifier.py
#
# Classification engine for Pelican Risk.
# Uses real confidence scoring (0.0–1.0) and writes
# every classification to the database for audit trail.

import re
import uuid
from app.confidence import (
    score_keyword_match, build_reasoning,
    needs_human_review, CONFIRMED_SCORE
)
from app.database import Classification

NAICS_MAPPINGS = {

    # ── ENERGY AND OIL & GAS ─────────────────────────────────
    "oilfield well servicing": {"code": "213112", "description": "Support Activities for Oil and Gas Operations", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "oilfield services":       {"code": "213112", "description": "Support Activities for Oil and Gas Operations", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "oilfield":                {"code": "213112", "description": "Support Activities for Oil and Gas Operations", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "oil field":               {"code": "213112", "description": "Support Activities for Oil and Gas Operations", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "offshore drilling":       {"code": "213111", "description": "Drilling Oil and Gas Wells", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "drilling":                {"code": "213111", "description": "Drilling Oil and Gas Wells", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "pipeline":                {"code": "486110", "description": "Pipeline Transportation of Crude Oil", "sector": "Transportation and Warehousing"},
    "petroleum refinery":      {"code": "324110", "description": "Petroleum Refineries", "sector": "Manufacturing"},
    "refinery":                {"code": "324110", "description": "Petroleum Refineries", "sector": "Manufacturing"},
    "petroleum":               {"code": "324110", "description": "Petroleum Refineries", "sector": "Manufacturing"},
    "offshore marine":         {"code": "483113", "description": "Coastal and Great Lakes Freight Transportation", "sector": "Transportation and Warehousing"},
    "offshore":                {"code": "213112", "description": "Support Activities for Oil and Gas Operations", "sector": "Mining, Quarrying, and Oil and Gas Extraction"},
    "energy":                  {"code": "221118", "description": "Other Electric Power Generation", "sector": "Utilities"},

    # ── MARINE AND PORT ───────────────────────────────────────
    "marine transportation":   {"code": "483211", "description": "Inland Water Freight Transportation", "sector": "Transportation and Warehousing"},
    "marine":                  {"code": "483211", "description": "Inland Water Freight Transportation", "sector": "Transportation and Warehousing"},
    "maritime":                {"code": "483211", "description": "Inland Water Freight Transportation", "sector": "Transportation and Warehousing"},
    "tugboat":                 {"code": "483211", "description": "Inland Water Freight Transportation", "sector": "Transportation and Warehousing"},
    "barge":                   {"code": "483211", "description": "Inland Water Freight Transportation", "sector": "Transportation and Warehousing"},
    "shipping":                {"code": "483113", "description": "Coastal and Great Lakes Freight Transportation", "sector": "Transportation and Warehousing"},
    "port":                    {"code": "488310", "description": "Port and Harbor Operations", "sector": "Transportation and Warehousing"},
    "vessel":                  {"code": "483211", "description": "Inland Water Freight Transportation", "sector": "Transportation and Warehousing"},

    # ── CONSTRUCTION ─────────────────────────────────────────
    "general construction":    {"code": "236220", "description": "Commercial and Institutional Building Construction", "sector": "Construction"},
    "construction":            {"code": "236220", "description": "Commercial and Institutional Building Construction", "sector": "Construction"},
    "electrical contractor":   {"code": "238210", "description": "Electrical Contractors and Other Wiring Installation", "sector": "Construction"},
    "electrical":              {"code": "238210", "description": "Electrical Contractors and Other Wiring Installation", "sector": "Construction"},
    "plumbing":                {"code": "238220", "description": "Plumbing, Heating, and Air-Conditioning Contractors", "sector": "Construction"},
    "hvac":                    {"code": "238220", "description": "Plumbing, Heating, and Air-Conditioning Contractors", "sector": "Construction"},
    "roofing":                 {"code": "238160", "description": "Roofing Contractors", "sector": "Construction"},
    "excavation":              {"code": "238910", "description": "Site Preparation Contractors", "sector": "Construction"},
    "concrete":                {"code": "238110", "description": "Poured Concrete Foundation and Structure Contractors", "sector": "Construction"},

    # ── FOOD AND RESTAURANT ───────────────────────────────────
    "full service restaurant": {"code": "722511", "description": "Full-Service Restaurants", "sector": "Accommodation and Food Services"},
    "restaurant":              {"code": "722511", "description": "Full-Service Restaurants", "sector": "Accommodation and Food Services"},
    "cafe":                    {"code": "722515", "description": "Snack and Nonalcoholic Beverage Bars", "sector": "Accommodation and Food Services"},
    "catering":                {"code": "722320", "description": "Caterers", "sector": "Accommodation and Food Services"},
    "crawfish":                {"code": "114112", "description": "Shellfish Fishing", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "oyster":                  {"code": "114112", "description": "Shellfish Fishing", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "seafood":                 {"code": "722511", "description": "Full-Service Restaurants", "sector": "Accommodation and Food Services"},
    "brewery":                 {"code": "312120", "description": "Breweries", "sector": "Manufacturing"},
    "bakery":                  {"code": "311811", "description": "Retail Bakeries", "sector": "Retail Trade"},
    "bar":                     {"code": "722410", "description": "Drinking Places (Alcoholic Beverages)", "sector": "Accommodation and Food Services"},

    # ── HEALTHCARE ────────────────────────────────────────────
    "general hospital":        {"code": "622110", "description": "General Medical and Surgical Hospitals", "sector": "Health Care and Social Assistance"},
    "hospital":                {"code": "622110", "description": "General Medical and Surgical Hospitals", "sector": "Health Care and Social Assistance"},
    "medical clinic":          {"code": "621111", "description": "Offices of Physicians", "sector": "Health Care and Social Assistance"},
    "clinic":                  {"code": "621111", "description": "Offices of Physicians", "sector": "Health Care and Social Assistance"},
    "pharmacy":                {"code": "446110", "description": "Pharmacies and Drug Stores", "sector": "Retail Trade"},
    "dental":                  {"code": "621210", "description": "Offices of Dentists", "sector": "Health Care and Social Assistance"},
    "medical":                 {"code": "621111", "description": "Offices of Physicians", "sector": "Health Care and Social Assistance"},
    "nursing home":            {"code": "623110", "description": "Nursing Care Facilities", "sector": "Health Care and Social Assistance"},
    "nursing":                 {"code": "623110", "description": "Nursing Care Facilities", "sector": "Health Care and Social Assistance"},
    "physical therapy":        {"code": "621340", "description": "Offices of Physical, Occupational and Speech Therapists", "sector": "Health Care and Social Assistance"},
    "therapy":                 {"code": "621340", "description": "Offices of Physical, Occupational and Speech Therapists", "sector": "Health Care and Social Assistance"},

    # ── FINANCE ───────────────────────────────────────────────
    "community bank":          {"code": "522110", "description": "Commercial Banking", "sector": "Finance and Insurance"},
    "national bank":           {"code": "522110", "description": "Commercial Banking", "sector": "Finance and Insurance"},
    "bank":                    {"code": "522110", "description": "Commercial Banking", "sector": "Finance and Insurance"},
    "credit union":            {"code": "522130", "description": "Credit Unions", "sector": "Finance and Insurance"},
    "insurance agency":        {"code": "524210", "description": "Insurance Agencies and Brokerages", "sector": "Finance and Insurance"},
    "insurance":               {"code": "524210", "description": "Insurance Agencies and Brokerages", "sector": "Finance and Insurance"},
    "mortgage":                {"code": "522310", "description": "Mortgage and Nonmortgage Loan Brokers", "sector": "Finance and Insurance"},
    "investment":              {"code": "523110", "description": "Investment Banking and Securities Dealing", "sector": "Finance and Insurance"},

    # ── REAL ESTATE ───────────────────────────────────────────
    "real estate agency":      {"code": "531210", "description": "Offices of Real Estate Agents and Brokers", "sector": "Real Estate and Rental and Leasing"},
    "real estate":             {"code": "531210", "description": "Offices of Real Estate Agents and Brokers", "sector": "Real Estate and Rental and Leasing"},
    "property management":     {"code": "531311", "description": "Residential Property Managers", "sector": "Real Estate and Rental and Leasing"},
    "apartment":               {"code": "531110", "description": "Lessors of Residential Buildings and Dwellings", "sector": "Real Estate and Rental and Leasing"},

    # ── RETAIL ────────────────────────────────────────────────
    "auto dealer":             {"code": "441110", "description": "New Car Dealers", "sector": "Retail Trade"},
    "car dealer":              {"code": "441110", "description": "New Car Dealers", "sector": "Retail Trade"},
    "grocery":                 {"code": "445110", "description": "Supermarkets and Other Grocery Retailers", "sector": "Retail Trade"},
    "convenience store":       {"code": "445131", "description": "Convenience Retailers", "sector": "Retail Trade"},
    "gas station":             {"code": "447110", "description": "Gasoline Stations with Convenience Stores", "sector": "Retail Trade"},
    "hardware":                {"code": "444110", "description": "Home Centers", "sector": "Retail Trade"},

    # ── PROFESSIONAL SERVICES ─────────────────────────────────
    "law firm":                {"code": "541110", "description": "Offices of Lawyers", "sector": "Professional, Scientific, and Technical Services"},
    "attorney":                {"code": "541110", "description": "Offices of Lawyers", "sector": "Professional, Scientific, and Technical Services"},
    "accounting firm":         {"code": "541211", "description": "Offices of Certified Public Accountants", "sector": "Professional, Scientific, and Technical Services"},
    "cpa":                     {"code": "541211", "description": "Offices of Certified Public Accountants", "sector": "Professional, Scientific, and Technical Services"},
    "engineering":             {"code": "541330", "description": "Engineering Services", "sector": "Professional, Scientific, and Technical Services"},
    "architecture":            {"code": "541310", "description": "Architectural Services", "sector": "Professional, Scientific, and Technical Services"},
    "consulting":              {"code": "541611", "description": "Administrative Management Consulting", "sector": "Professional, Scientific, and Technical Services"},
    "staffing":                {"code": "561320", "description": "Temporary Help Services", "sector": "Administrative and Support Services"},

    # ── TRANSPORTATION ────────────────────────────────────────
    "trucking":                {"code": "484110", "description": "General Freight Trucking, Local", "sector": "Transportation and Warehousing"},
    "freight":                 {"code": "484110", "description": "General Freight Trucking, Local", "sector": "Transportation and Warehousing"},
    "logistics":               {"code": "541614", "description": "Process, Physical Distribution Consulting", "sector": "Professional, Scientific, and Technical Services"},
    "warehouse":               {"code": "493110", "description": "General Warehousing and Storage", "sector": "Transportation and Warehousing"},

    # ── AGRICULTURE ───────────────────────────────────────────
    "sugarcane":               {"code": "111930", "description": "Sugarcane Farming", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "cotton":                  {"code": "111920", "description": "Cotton Farming", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "rice":                    {"code": "111160", "description": "Rice Farming", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "catfish":                 {"code": "112511", "description": "Finfish Farming and Fish Hatcheries", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "shrimp":                  {"code": "114112", "description": "Shellfish Fishing", "sector": "Agriculture, Forestry, Fishing and Hunting"},
    "timber":                  {"code": "113110", "description": "Timber Tract Operations", "sector": "Agriculture, Forestry, Fishing and Hunting"},

    # ── PERSONAL SERVICES ─────────────────────────────────────
    "salon":                   {"code": "812112", "description": "Beauty Salons", "sector": "Other Services"},
    "barber":                  {"code": "812111", "description": "Barber Shops", "sector": "Other Services"},
    "funeral home":            {"code": "812210", "description": "Funeral Homes and Funeral Services", "sector": "Other Services"},
    "funeral":                 {"code": "812210", "description": "Funeral Homes and Funeral Services", "sector": "Other Services"},
    "laundry":                 {"code": "812310", "description": "Coin-Operated Laundries and Drycleaners", "sector": "Other Services"},
    "cleaning":                {"code": "561720", "description": "Janitorial Services", "sector": "Administrative and Support Services"},
    "landscaping":             {"code": "561730", "description": "Landscaping Services", "sector": "Administrative and Support Services"},
    "security":                {"code": "561612", "description": "Security Guards and Patrol Services", "sector": "Administrative and Support Services"},

    # ── GENERIC FALLBACK ─────────────────────────────────────
    "contractor":              {"code": "238990", "description": "All Other Specialty Trade Contractors", "sector": "Construction"},
    "services":                {"code": "561499", "description": "All Other Business Support Services", "sector": "Administrative and Support Services"},
    "solutions":               {"code": "561499", "description": "All Other Business Support Services", "sector": "Administrative and Support Services"},
    "management":              {"code": "551114", "description": "Corporate, Subsidiary, and Regional Managing Offices", "sector": "Management of Companies"},
    "holdings":                {"code": "551114", "description": "Corporate, Subsidiary, and Regional Managing Offices", "sector": "Management of Companies"},
    "group":                   {"code": "551114", "description": "Corporate, Subsidiary, and Regional Managing Offices", "sector": "Management of Companies"},
    "enterprises":             {"code": "551114", "description": "Corporate, Subsidiary, and Regional Managing Offices", "sector": "Management of Companies"},
}

GENERIC_KEYWORDS = {
    "contractor", "services", "solutions", "group",
    "company", "enterprises", "industries", "management",
    "associates", "partners", "holdings", "ventures"
}


def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def find_all_keyword_matches(business_name):
    """Returns ALL keyword matches, sorted by length (most specific first)."""
    normalized = normalize(business_name)
    matches = []
    sorted_keywords = sorted(NAICS_MAPPINGS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in normalized:
            match = NAICS_MAPPINGS[keyword]
            matches.append({
                "match_keyword": keyword,
                "naics_code": match["code"],
                "naics_description": match["description"],
                "naics_sector": match["sector"],
                "is_generic": keyword in GENERIC_KEYWORDS,
            })
    return matches


def classify_business(business_name, address=None, customer_id=None, batch_id=None, db=None):
    """
    Main classification function.
    Pipeline: find all matches → score best match → build reasoning → persist to DB.
    db parameter is optional so this works without a database in tests.
    """
    if not business_name or not business_name.strip():
        return {"success": False, "error": "Business name is required"}

    all_matches = find_all_keyword_matches(business_name)

    # Extract parish from address
    parish = None
    if address:
        la_parishes = [
            "orleans", "jefferson", "east baton rouge", "caddo", "lafayette",
            "st tammany", "calcasieu", "ouachita", "bossier", "st landry",
            "terrebonne", "tangipahoa", "rapides", "livingston", "iberia",
            "ascension", "acadia", "st mary", "natchitoches", "vermilion"
        ]
        addr_lower = address.lower()
        for p in la_parishes:
            if p in addr_lower:
                parish = p.title()
                break

    # No match found
    if not all_matches:
        result = {
            "success": False,
            "business_name": business_name,
            "address": address,
            "parish": parish,
            "naics_code": None,
            "naics_description": "Could not classify this business",
            "naics_sector": None,
            "confidence_score": 0.0,
            "confidence_tier": "unclassified",
            "needs_review": True,
            "method": "no_match",
            "match_keyword": None,
            "match_count": 0,
            "conflict_detected": False,
            "reasoning": "No keyword match found. Manual classification required.",
            "batch_id": batch_id,
        }
        if db and customer_id:
            _persist(result, customer_id, db)
        return result

    # Prefer specific matches over generic ones
    specific = [m for m in all_matches if not m["is_generic"]]
    generic  = [m for m in all_matches if m["is_generic"]]
    best_pool = specific if specific else generic
    best = best_pool[0]

    score, tier, conflict = score_keyword_match(
        keyword=best["match_keyword"],
        all_matches=all_matches,
        is_generic=best["is_generic"],
    )

    reasoning = build_reasoning(
        keyword=best["match_keyword"],
        all_matches=all_matches,
        conflict_detected=conflict,
        score=score,
        method="keyword",
    )

    result = {
        "success": True,
        "business_name": business_name,
        "address": address,
        "parish": parish,
        "naics_code": best["naics_code"],
        "naics_description": best["naics_description"],
        "naics_sector": best["naics_sector"],
        "confidence_score": score,
        "confidence_tier": tier,
        "needs_review": needs_human_review(score),
        "method": "keyword",
        "match_keyword": best["match_keyword"],
        "match_count": len(all_matches),
        "conflict_detected": conflict,
        "reasoning": reasoning,
        "batch_id": batch_id,
    }

    if db and customer_id:
        _persist(result, customer_id, db)

    return result


def _persist(result, customer_id, db):
    """Writes a classification result to the database."""
    record = Classification(
        id=str(uuid.uuid4()),
        customer_id=customer_id,
        business_name=result["business_name"],
        address=result.get("address"),
        parish=result.get("parish"),
        naics_code=result.get("naics_code"),
        naics_description=result.get("naics_description"),
        naics_sector=result.get("naics_sector"),
        confidence_score=result.get("confidence_score"),
        confidence_tier=result.get("confidence_tier"),
        needs_review=result.get("needs_review", False),
        method=result.get("method", "unknown"),
        match_keyword=result.get("match_keyword"),
        match_count=result.get("match_count", 0),
        conflict_detected=result.get("conflict_detected", False),
        reasoning=result.get("reasoning"),
        batch_id=result.get("batch_id"),
    )
    db.add(record)
    db.commit()