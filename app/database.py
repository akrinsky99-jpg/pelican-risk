# app/database.py
#
# Database layer for Pelican Risk.
# Four tables: customers, classifications, corrections, batch_jobs.
# This is what separates the product from a chatbot —
# persistent, auditable, customer-isolated records.
#
# SQLite for local dev. Swap connection string to Postgres for production.

from sqlalchemy import (
    create_engine, Column, String, Float, Boolean,
    DateTime, Text, Integer, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import uuid

DATABASE_URL = "sqlite:///./pelican_risk.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ── TABLE 1: CUSTOMERS ────────────────────────────────────────
# One row per institution. Every other table is scoped to
# customer_id so institutions never see each other's data.

class Customer(Base):
    __tablename__ = "customers"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = Column(String, nullable=False)
    type       = Column(String, nullable=False)   # "bank" | "credit_union" | "insurance"
    state      = Column(String, default="LA")
    api_key    = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    active     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    classifications = relationship("Classification", back_populates="customer")


# ── TABLE 2: CLASSIFICATIONS ──────────────────────────────────
# Core record. Every classification written here permanently.
# confidence_score is a real float (0.0–1.0), not a string.

class Classification(Base):
    __tablename__ = "classifications"

    id                = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id       = Column(String, ForeignKey("customers.id"), nullable=False)

    # Input
    business_name     = Column(String, nullable=False)
    address           = Column(String)
    parish            = Column(String)

    # Output
    naics_code        = Column(String)
    naics_description = Column(String)
    naics_sector      = Column(String)

    # Confidence
    confidence_score  = Column(Float)
    confidence_tier   = Column(String)    # "high" | "medium" | "low" | "unclassified"
    needs_review      = Column(Boolean, default=False)

    # Method
    method            = Column(String)    # "keyword" | "llm_assist" | "manual"
    match_keyword     = Column(String)
    match_count       = Column(Integer, default=0)
    conflict_detected = Column(Boolean, default=False)
    reasoning         = Column(Text)

    # Human review
    confirmed         = Column(Boolean, default=False)
    confirmed_by      = Column(String)
    confirmed_at      = Column(DateTime)

    # Metadata
    batch_id          = Column(String)
    created_at        = Column(DateTime, default=datetime.utcnow)

    customer    = relationship("Customer", back_populates="classifications")
    corrections = relationship("Correction", back_populates="classification")


# ── TABLE 3: CORRECTIONS ─────────────────────────────────────
# Every human override stored permanently — never overwrites
# the original. This table is the proprietary dataset
# that becomes the moat over time.

class Correction(Base):
    __tablename__ = "corrections"

    id                    = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    classification_id     = Column(String, ForeignKey("classifications.id"), nullable=False)
    customer_id           = Column(String, nullable=False)

    original_naics_code   = Column(String)
    corrected_naics_code  = Column(String, nullable=False)
    corrected_description = Column(String)
    corrected_sector      = Column(String)
    correction_reason     = Column(Text)
    corrected_by          = Column(String)
    corrected_at          = Column(DateTime, default=datetime.utcnow)

    classification = relationship("Classification", back_populates="corrections")


# ── TABLE 4: BATCH JOBS ───────────────────────────────────────
# Tracks CSV upload jobs so banks can submit 500 businesses
# at once and check progress.

class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id  = Column(String, ForeignKey("customers.id"), nullable=False)
    filename     = Column(String)
    total_rows   = Column(Integer, default=0)
    classified   = Column(Integer, default=0)
    needs_review = Column(Integer, default=0)
    failed       = Column(Integer, default=0)
    status       = Column(String, default="pending")  # "pending"|"processing"|"complete"|"error"
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


# ── HELPERS ───────────────────────────────────────────────────

def get_db():
    """Dependency injection for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at startup."""
    Base.metadata.create_all(bind=engine)


def seed_demo_customer():
    """Creates a demo bank for local testing. Returns its API key."""
    db = SessionLocal()
    existing = db.query(Customer).filter_by(name="Demo Bank of Louisiana").first()
    if existing:
        db.close()
        return existing.api_key

    demo = Customer(
        name="Demo Bank of Louisiana",
        type="bank",
        state="LA",
    )
    db.add(demo)
    db.commit()
    db.refresh(demo)
    key = demo.api_key
    db.close()
    return key


if __name__ == "__main__":
    init_db()
    key = seed_demo_customer()
    print(f"Database initialized.")
    print(f"Demo API key: {key}")
    print("Tables: customers, classifications, corrections, batch_jobs")