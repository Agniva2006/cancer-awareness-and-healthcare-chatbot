"""Seed the knowledge_documents table from the JSON files (idempotent).

Usage:
    python scripts/seed_knowledge.py            # seed all JSON entries
    python scripts/seed_knowledge.py --reset    # wipe + reseed
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.knowledge import KnowledgeDocument  # noqa: E402

CATEGORY_FALLBACK = "general"


def slugify(title: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in title.lower())[:120].strip("-")


def load_json_docs() -> list[dict]:
    docs = []
    for path in settings.KNOWLEDGE_FILES:
        if not path.exists():
            print(f"SKIP (missing): {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            item["_source_file"] = path.name
        docs.extend(raw)
    return docs


def seed(reset: bool = False) -> None:
    db = SessionLocal()
    try:
        if reset:
            n = db.query(KnowledgeDocument).delete()
            db.commit()
            print(f"Reset: deleted {n} existing documents")

        added, skipped = 0, 0
        for item in load_json_docs():
            title = item.get("title", "").strip()
            content = item.get("content", "").strip()
            if not title or not content:
                skipped += 1
                continue

            ext_key = item.get("id") or slugify(title)
            exists = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.external_key == ext_key)
                .first()
            )
            if exists:
                skipped += 1
                continue

            db.add(
                KnowledgeDocument(
                    title=title,
                    content=content,
                    source=item.get("source", ""),
                    category=item.get("category", CATEGORY_FALLBACK),
                    cancer_type=item.get("cancer_type", "general"),
                    difficulty="professional" if item.get("icd10") else "patient",
                    external_key=ext_key,
                )
            )
            added += 1

        db.commit()
        total = db.query(KnowledgeDocument).count()
        print(f"Seeded: {added} added, {skipped} skipped, {total} total documents")
    finally:
        db.close()


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
