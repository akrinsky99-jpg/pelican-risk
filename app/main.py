# app/main.py
#
# This file creates the FastAPI web server that exposes
# the classifier as a REST API.
#
# A REST API is just a web service that accepts HTTP requests
# and returns JSON responses. When your classifier lives
# behind an API, any application can use it — a web browser,
# a mobile app, another company's software, or a bank's
# loan processing system.
#
# FastAPI is one of the simplest and fastest Python web
# frameworks available. It automatically generates
# interactive documentation at /docs so you can test
# your API in the browser without writing any extra code.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.classifier import classify_business, NAICS_MAPPINGS


# ── APP INITIALIZATION ────────────────────────────────────────
# Create the FastAPI application instance.
# The title and description appear in the auto-generated
# documentation at /docs

app = FastAPI(
    title="Louisiana NAICS Classifier API",
    description="""
    Classifies Louisiana businesses by NAICS industry code
    using business name and address as input.
    
    Built for community banks, credit unions, and insurance
    agencies who need fast, accurate business classification
    without enterprise pricing.
    """,
    version="0.1.0"
)


# ── CORS MIDDLEWARE ───────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) controls which websites
# can call your API from their browser.
# allow_origins=["*"] means any website can call this API.
# In production you'd restrict this to specific domains.
# For an MVP and competition demo, open access is fine.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ── REQUEST AND RESPONSE MODELS ───────────────────────────────
# Pydantic models define the exact shape of data the API
# accepts and returns. FastAPI uses these to:
# 1. Validate incoming requests automatically
# 2. Generate accurate API documentation
# 3. Return helpful error messages for bad input

class ClassifyRequest(BaseModel):
    """
    The data structure the API expects to receive.
    business_name is required.
    address is optional but improves future accuracy.
    """
    business_name: str
    address: Optional[str] = None

    # Example data that appears in the /docs interface
    # so users can see exactly what to send
    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Gulf Coast Oilfield Services LLC",
                "address": "Lafayette, LA 70501"
            }
        }


class ClassifyResponse(BaseModel):
    """
    The data structure the API always returns.
    Every field is documented so API consumers know
    exactly what to expect in every response.
    """
    success: bool           # True if classified, False if not
    business_name: str      # The input business name
    address: Optional[str]  # The input address
    naics_code: Optional[str]       # 6-digit NAICS code
    description: Optional[str]      # Industry description
    sector: Optional[str]           # Broad industry sector
    confidence: str                 # high / medium / none
    match_keyword: Optional[str]    # Which keyword triggered the match
    method: str                     # How it was classified


# ── API ENDPOINTS ─────────────────────────────────────────────
# Each function below is one API endpoint — one URL that
# accepts requests and returns responses.
#
# The @app decorator tells FastAPI what HTTP method (GET/POST)
# and URL path (/classify) this function handles.

@app.get("/")
def root():
    """
    Root endpoint — confirms the API is running.
    Useful for health checks and deployment verification.
    Visit the base URL to see this response.
    """
    return {
        "name": "Louisiana NAICS Classifier API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "classify": "/classify",
            "batch": "/classify/batch",
            "coverage": "/coverage",
            "health": "/health"
        }
    }


@app.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest):
    """
    Main classification endpoint.
    
    Accepts a business name and optional address.
    Returns the predicted NAICS code and industry description.
    
    Example request:
    POST /classify
    {
        "business_name": "Pelican State Credit Union",
        "address": "Baton Rouge, LA"
    }
    
    Example response:
    {
        "success": true,
        "naics_code": "522130",
        "description": "Credit Unions",
        "sector": "Finance and Insurance",
        "confidence": "high"
    }
    """
    # Call the classifier function from classifier.py
    result = classify_business(
        business_name=request.business_name,
        address=request.address
    )

    # If the input was invalid (empty business name etc)
    # return a 400 Bad Request HTTP error
    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )

    return result


@app.post("/classify/batch")
def classify_batch(requests: list[ClassifyRequest]):
    """
    Batch classification endpoint.
    
    Accepts a list of businesses and classifies all of them
    in one API call. Much more efficient than calling
    /classify once per business when you have many to process.
    
    Useful for banks processing loan applications in bulk
    or insurance agencies onboarding multiple clients.
    
    Maximum 100 businesses per batch request.
    """
    # Enforce a reasonable batch size limit
    if len(requests) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 businesses per batch request"
        )

    # Classify each business and collect results
    results = []
    for req in requests:
        result = classify_business(
            business_name=req.business_name,
            address=req.address
        )
        results.append(result)

    # Return summary statistics alongside the results
    # so the caller immediately knows how well the
    # batch classified
    classified = sum(1 for r in results if r["success"])

    return {
        "total": len(results),
        "classified": classified,
        "unclassified": len(results) - classified,
        "accuracy_rate": round(classified / len(results) * 100, 1),
        "results": results
    }


@app.get("/coverage")
def coverage():
    """
    Returns the list of industries and keywords the
    classifier currently covers.
    
    Useful for API consumers to understand what business
    types will classify successfully before sending requests.
    Also shows investors and judges exactly how many
    industries the system covers.
    """
    # Group keywords by sector for a cleaner response
    sectors = {}
    for keyword, data in NAICS_MAPPINGS.items():
        sector = data["sector"]
        if sector not in sectors:
            sectors[sector] = {
                "sector": sector,
                "keywords": [],
                "naics_codes": set()
            }
        sectors[sector]["keywords"].append(keyword)
        sectors[sector]["naics_codes"].add(data["code"])

    # Convert sets to lists for JSON serialization
    # (JSON doesn't support Python sets)
    sector_list = []
    for sector_data in sectors.values():
        sector_list.append({
            "sector": sector_data["sector"],
            "keyword_count": len(sector_data["keywords"]),
            "keywords": sorted(sector_data["keywords"]),
            "unique_naics_codes": len(sector_data["naics_codes"])
        })

    return {
        "total_keywords": len(NAICS_MAPPINGS),
        "total_sectors": len(sectors),
        "sectors": sorted(sector_list, key=lambda x: x["keyword_count"], reverse=True)
    }


@app.get("/health")
def health():
    """
    Health check endpoint.
    Returns basic system status.
    Used by deployment platforms to verify the API
    is running correctly.
    """
    return {
        "status": "healthy",
        "classifier_keywords": len(NAICS_MAPPINGS),
        "version": "0.1.0"
    }