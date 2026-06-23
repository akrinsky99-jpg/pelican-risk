# app/main.py — Pelican Risk API
# Endpoints: classify, batch, correct, confirm, history, audit, portfolio

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from app.classifier import classify_business, NAICS_MAPPINGS
from app.database import (
    get_db, init_db, seed_demo_customer,
    Customer, Classification, Correction, BatchJob
)
from app.confidence import CONFIRMED_SCORE

app = FastAPI(
    title="Pelican Risk API",
    description="NAICS classification and portfolio intelligence for Louisiana financial institutions.",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup():
    init_db()
    seed_demo_customer()


# ── AUTH ──────────────────────────────────────────────────────

def get_customer(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> Customer:
    customer = db.query(Customer).filter_by(api_key=x_api_key, active=True).first()
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return customer


# ── REQUEST MODELS ────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    business_name: str
    address: Optional[str] = None

class BatchRequest(BaseModel):
    businesses: list[ClassifyRequest]

class CorrectRequest(BaseModel):
    corrected_naics_code: str
    corrected_description: Optional[str] = None
    corrected_sector: Optional[str] = None
    correction_reason: Optional[str] = None
    corrected_by: Optional[str] = "reviewer"

class ConfirmRequest(BaseModel):
    confirmed_by: Optional[str] = "reviewer"


# ── ENDPOINTS ─────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "Pelican Risk API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "classifier_keywords": len(NAICS_MAPPINGS),
        "version": "0.2.0"
    }


@app.post("/classify")
def classify(
    req: ClassifyRequest,
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """Classify a single business. Writes result to database."""
    result = classify_business(
        business_name=req.business_name,
        address=req.address,
        customer_id=customer.id,
        db=db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/classify/batch")
def classify_batch(
    req: BatchRequest,
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """Classify up to 500 businesses at once. All results stored with a shared batch_id."""
    if len(req.businesses) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 businesses per batch")

    batch_id = str(uuid.uuid4())
    job = BatchJob(
        id=batch_id,
        customer_id=customer.id,
        total_rows=len(req.businesses),
        status="processing"
    )
    db.add(job)
    db.commit()

    results = []
    classified = needs_review = failed = 0

    for b in req.businesses:
        try:
            result = classify_business(
                business_name=b.business_name,
                address=b.address,
                customer_id=customer.id,
                batch_id=batch_id,
                db=db,
            )
            results.append(result)
            if result.get("success"):
                classified += 1
            if result.get("needs_review"):
                needs_review += 1
        except Exception:
            failed += 1
            results.append({
                "success": False,
                "business_name": b.business_name,
                "error": "Processing error"
            })

    job.classified = classified
    job.needs_review = needs_review
    job.failed = failed
    job.status = "complete"
    job.completed_at = datetime.utcnow()
    db.commit()

    return {
        "batch_id": batch_id,
        "total": len(req.businesses),
        "classified": classified,
        "needs_review": needs_review,
        "failed": failed,
        "results": results,
    }


@app.put("/classifications/{classification_id}/correct")
def correct_classification(
    classification_id: str,
    req: CorrectRequest,
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """
    Human correction endpoint.
    Stores the original and corrected code permanently.
    Every correction is proprietary training signal.
    """
    record = db.query(Classification).filter_by(
        id=classification_id, customer_id=customer.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Classification not found")

    correction = Correction(
        classification_id=classification_id,
        customer_id=customer.id,
        original_naics_code=record.naics_code,
        corrected_naics_code=req.corrected_naics_code,
        corrected_description=req.corrected_description,
        corrected_sector=req.corrected_sector,
        correction_reason=req.correction_reason,
        corrected_by=req.corrected_by,
    )
    db.add(correction)

    record.naics_code = req.corrected_naics_code
    if req.corrected_description:
        record.naics_description = req.corrected_description
    if req.corrected_sector:
        record.naics_sector = req.corrected_sector
    record.confidence_score = CONFIRMED_SCORE
    record.confidence_tier = "high"
    record.needs_review = False
    record.confirmed = True
    record.confirmed_by = req.corrected_by
    record.confirmed_at = datetime.utcnow()
    record.method = "manual"
    record.reasoning = f"Manually corrected by {req.corrected_by}. Reason: {req.correction_reason or 'not provided'}."

    db.commit()
    return {
        "success": True,
        "classification_id": classification_id,
        "corrected_to": req.corrected_naics_code
    }


@app.put("/classifications/{classification_id}/confirm")
def confirm_classification(
    classification_id: str,
    req: ConfirmRequest,
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """Human confirms a classification is correct as-is. Locks confidence at 1.0."""
    record = db.query(Classification).filter_by(
        id=classification_id, customer_id=customer.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Classification not found")

    record.confirmed = True
    record.confirmed_by = req.confirmed_by
    record.confirmed_at = datetime.utcnow()
    record.confidence_score = CONFIRMED_SCORE
    record.needs_review = False
    db.commit()
    return {
        "success": True,
        "classification_id": classification_id,
        "confirmed_by": req.confirmed_by
    }


@app.get("/history")
def classification_history(
    limit: int = 50,
    needs_review: Optional[bool] = None,
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """Classification history for this institution. Filter by needs_review=true to see the review queue."""
    query = db.query(Classification).filter_by(customer_id=customer.id)
    if needs_review is not None:
        query = query.filter_by(needs_review=needs_review)
    records = query.order_by(Classification.created_at.desc()).limit(limit).all()
    return {
        "customer": customer.name,
        "total_returned": len(records),
        "results": [_serialize(r) for r in records]
    }


@app.get("/audit/{classification_id}")
def audit_trail(
    classification_id: str,
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """
    Full audit trail for a single classification.
    This is what you show an examiner.
    """
    record = db.query(Classification).filter_by(
        id=classification_id, customer_id=customer.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Classification not found")

    corrections = db.query(Correction).filter_by(
        classification_id=classification_id
    ).all()

    return {
        "classification": _serialize(record),
        "correction_history": [
            {
                "original_code": c.original_naics_code,
                "corrected_to": c.corrected_naics_code,
                "corrected_by": c.corrected_by,
                "reason": c.correction_reason,
                "corrected_at": c.corrected_at.isoformat() if c.corrected_at else None,
            }
            for c in corrections
        ],
        "audit_summary": {
            "total_corrections": len(corrections),
            "currently_confirmed": record.confirmed,
            "final_code": record.naics_code,
            "final_confidence": record.confidence_score,
        }
    }


@app.get("/portfolio/concentration")
def portfolio_concentration(
    customer: Customer = Depends(get_customer),
    db: Session = Depends(get_db)
):
    """
    Layer 2: Portfolio concentration dashboard.
    Breakdown of classified businesses by sector.
    Flags any sector exceeding 20% concentration.
    This is the Chief Risk Officer view.
    """
    records = db.query(Classification).filter(
        Classification.customer_id == customer.id,
        Classification.naics_code != None
    ).all()

    if not records:
        return {"customer": customer.name, "total_classified": 0, "sectors": []}

    sector_counts = {}
    for r in records:
        sector = r.naics_sector or "Unknown"
        if sector not in sector_counts:
            sector_counts[sector] = {"sector": sector, "count": 0, "businesses": []}
        sector_counts[sector]["count"] += 1
        sector_counts[sector]["businesses"].append(r.business_name)

    total = len(records)
    sectors = sorted(sector_counts.values(), key=lambda x: x["count"], reverse=True)

    for s in sectors:
        pct = round(s["count"] / total * 100, 1)
        s["percentage"] = pct
        s["concentration_warning"] = pct > 20.0

    return {
        "customer": customer.name,
        "total_classified": total,
        "concentration_warning_threshold_pct": 20.0,
        "sectors": sectors,
    }


def _serialize(r):
    return {
        "id": r.id,
        "business_name": r.business_name,
        "address": r.address,
        "parish": r.parish,
        "naics_code": r.naics_code,
        "naics_description": r.naics_description,
        "naics_sector": r.naics_sector,
        "confidence_score": r.confidence_score,
        "confidence_tier": r.confidence_tier,
        "needs_review": r.needs_review,
        "confirmed": r.confirmed,
        "confirmed_by": r.confirmed_by,
        "method": r.method,
        "match_keyword": r.match_keyword,
        "reasoning": r.reasoning,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }