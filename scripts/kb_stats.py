"""Dev helper: fetch the knowledge-base stats."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

for path in settings.KNOWLEDGE_FILES:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            docs = json.load(f)
        print(f"{path.name}: {len(docs)} documents")
    else:
        print(f"{path.name}: MISSING")
