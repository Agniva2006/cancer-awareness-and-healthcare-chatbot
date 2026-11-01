"""Quick retrieval quality check (dev tool, not part of the app)."""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING)

from app.services.rag import retrieve, grounding_ok, data  # noqa: E402

print(f"{len(data)} docs loaded")

queries = [
    "EGFR exon 19 deletion targeted therapy",
    "my scan showed something",
    "fever after chemo",
    "what is zzqqxx nothing",
    "who should get lung cancer screening",
]
for q in queries:
    t0 = time.perf_counter()
    r = retrieve(q, k=3)
    ms = (time.perf_counter() - t0) * 1000
    titles = [x["title"][:45] for x in r]
    print(f"{q!r:55} {ms:5.0f}ms  grounding={grounding_ok(r)}  {titles}")
