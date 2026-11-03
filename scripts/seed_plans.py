"""Seed the plans table (free / pro / clinic) — idempotent.

Run once per environment:  python -m scripts.seed_plans
Re-running updates prices/features but never duplicates plan codes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models.billing import Plan  # noqa: E402

PLANS = [
    {
        "code": "free",
        "name": "Free",
        "monthly_quota": 20,
        "price_cents": 0,
        "features": {"mode": "patient", "chat_export": False},
    },
    {
        "code": "pro",
        "name": "Pro",
        "monthly_quota": 100000,  # effectively unlimited for individuals
        "price_cents": 900,  # $9.00/month — integer cents, NEVER float
        "features": {
            "unlimited_queries": True,
            "clinical_mode": True,
            "priority_latency": True,
            "chat_export": True,
        },
    },
    {
        "code": "clinic",
        "name": "Clinic",
        "monthly_quota": 500000,
        "price_cents": 4900,  # $49.00/month
        "features": {
            "everything_in_pro": True,
            "team_seats": 5,
            "admin_dashboard": True,
            "usage_analytics": True,
        },
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for spec in PLANS:
            plan = db.query(Plan).filter(Plan.code == spec["code"]).first()
            if plan is None:
                db.add(Plan(**spec))
                print(f"created plan: {spec['code']}")
            else:
                for key, value in spec.items():
                    setattr(plan, key, value)
                print(f"updated plan: {spec['code']}")
        db.commit()
    finally:
        db.close()
    print("plans seeded.")


if __name__ == "__main__":
    seed()
