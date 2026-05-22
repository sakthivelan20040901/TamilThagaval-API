"""
database.py — Dataset loader, transformer, and query engine.

To add a new dataset:
  1. Add its key + path to DATASET_PATHS.
  2. If it needs flattening/transformation, add a method _transform_<key>
     and register it in DATASET_TRANSFORMS.
  That's it. No other file needs to change.
"""

import os
import json
import random
from typing import Any

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# 1. Dataset registry — add new datasets here only
# ---------------------------------------------------------------------------

# All paths are relative to this file, so the project works anywhere —
# locally, on Railway, Render, or any VPS. Just keep JSON files in data/.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATASET_PATHS: dict[str, str] = {
    "narrinai":    os.path.join(BASE_DIR, "data", "narrinai_clean1.json"),
    "kurunthogai": os.path.join(BASE_DIR, "data", "kurunthokai_cleaned.json"),
    "ainkurunuru": os.path.join(BASE_DIR, "data", "aingurunuru_cleaned.json"),
    "kalithogai":  os.path.join(BASE_DIR, "data", "kalithogai_cleaned.json"),  # ← add this
    # "purananuru":  os.path.join(BASE_DIR, "data", "purananuru.json"),  ← future datasets
}

# Maps dataset keys to their transform method name (if any).
# Datasets not listed here are loaded as-is.
DATASET_TRANSFORMS: dict[str, str] = {
    "ainkurunuru": "_transform_ainkurunuru",
    "kalithogai": "_transform_kalithogai",
    # "purananuru": "_transform_purananuru",
}


# Fields searched by the full-text search endpoint.
SEARCH_FIELDS: list[str] = [
    "poem", "poet", "topic", "note",
    "explanation", "mudippu", "karuthu",
]


# ---------------------------------------------------------------------------
# 2. Database class
# ---------------------------------------------------------------------------

class TamilLiteratureDB:
    """
    In-memory database for Tamil Sangam literature datasets.
    Loads and indexes all datasets at startup.
    """

    def __init__(self) -> None:
        self.datasets: dict[str, list[dict]] = {}
        self._load_all()

    # -----------------------------------------------------------------------
    # Startup loading
    # -----------------------------------------------------------------------

    def _load_all(self) -> None:
        """Load every registered dataset into memory."""
        for name, path in DATASET_PATHS.items():
            if not os.path.exists(path):
                print(f"⚠️  [{name}] File not found at: {path}")
                self.datasets[name] = []
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw: Any = json.load(f)

                transform_method = DATASET_TRANSFORMS.get(name)
                if transform_method:
                    transformer = getattr(self, transform_method)
                    self.datasets[name] = transformer(raw)
                else:
                    self.datasets[name] = raw

                print(f"✅ [{name}] Loaded {len(self.datasets[name])} poems.")

            except json.JSONDecodeError as e:
                print(f"❌ [{name}] JSON parse error: {e}")
                self.datasets[name] = []
            except Exception as e:
                print(f"❌ [{name}] Unexpected error: {e}")
                self.datasets[name] = []

    # -----------------------------------------------------------------------
    # Dataset transformers
    # Each transformer receives raw JSON and returns a flat list of poems.
    # Add a new _transform_<name> method for any new dataset that needs it.
    # -----------------------------------------------------------------------

    def _transform_ainkurunuru(self, raw: list[dict]) -> list[dict]:
        """
        Ainkurunuru is grouped by page/topic.
        Flatten it so every poem is a top-level record with topic + note.
        """
        flattened: list[dict] = []
        for page in raw:
            page_title = page.get("page_title", "")
            page_note  = page.get("page_note", "")
            for poem in page.get("poems", []):
                poem["topic"] = page_title
                poem["note"]  = page_note
                flattened.append(poem)
        return flattened

    def _transform_kalithogai(self, raw: Any) -> list[dict]:
        """Transform Kalithogai JSON into a flat list of poem records.

        Expected input formats (handled defensively):
        1) Already-flat: list[dict] with poem fields.
        2) Grouped: list[dict] where each group contains poems under a key
           like 'poems', 'verses', or similar; group metadata becomes topic/note.
        """
        if isinstance(raw, list) and (not raw or isinstance(raw[0], dict)):
            # Heuristic: if dicts already look like poems (contain poem text keys)
            # just return as-is.
            sample = raw[0] if raw else {}
            if "poem" in sample or "poet" in sample or "poem_number" in sample:
                return raw  # type: ignore[return-value]

            flattened: list[dict] = []
            for group in raw:
                if not isinstance(group, dict):
                    continue
                group_title = (
                    group.get("page_title")
                    or group.get("title")
                    or group.get("topic")
                    or ""
                )
                group_note = group.get("page_note") or group.get("note") or ""

                poems = (
                    group.get("poems")
                    or group.get("verses")
                    or group.get("items")
                    or []
                )
                for poem in poems if isinstance(poems, list) else []:
                    if not isinstance(poem, dict):
                        continue
                    poem["topic"] = poem.get("topic", group_title)
                    poem["note"] = poem.get("note", group_note)
                    flattened.append(poem)

            return flattened

        # Fallback: unknown structure => no poems.
        return []

    # Example stub for a future dataset with a different structure:
    # def _transform_purananuru(self, raw: list[dict]) -> list[dict]:
    #     return [{"poem_number": p["no"], **p} for p in raw]


    # -----------------------------------------------------------------------
    # Access helpers
    # -----------------------------------------------------------------------

    @property
    def available_collections(self) -> list[str]:
        return list(self.datasets.keys())

    def get_dataset(self, name: str) -> list[dict]:
        """
        Return the dataset for `name`.
        Case-insensitive — 'Kurunthogai' and 'kurunthogai' both work.
        Raises 404 for unknown names, 503 if the dataset failed to load.
        """
        name = name.strip().lower()
        if name not in self.datasets:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"Unknown collection '{name}'.",
                    "available": self.available_collections,
                },
            )
        if not self.datasets[name]:
            raise HTTPException(
                status_code=503,
                detail=f"Collection '{name}' exists but failed to load. Check server logs.",
            )
        return self.datasets[name]

    # -----------------------------------------------------------------------
    # Query methods
    # -----------------------------------------------------------------------

    @staticmethod
    def _normalize(text: Any) -> str:
        return " ".join(str(text).strip().split()).lower()

    def get_all(self, collection: str) -> list[dict]:
        return self.get_dataset(collection)

    def get_random(self, collection: str) -> dict:
        return random.choice(self.get_dataset(collection))

    def find_by_number(self, collection: str, poem_number: int) -> dict | None:
        for poem in self.get_dataset(collection):
            p_id = poem.get("poem_number", poem.get("id"))
            if str(p_id) == str(poem_number):
                return poem
        return None

    def filter_by_field(self, collection: str, field: str, query: str) -> list[dict]:
        data  = self.get_dataset(collection)
        query = self._normalize(query)
        return [p for p in data if query in self._normalize(p.get(field, ""))]

    def search(self, collection: str, query: str) -> list[dict]:
        data  = self.get_dataset(collection)
        query = self._normalize(query)
        return [
            p for p in data
            if any(query in self._normalize(p.get(f, "")) for f in SEARCH_FIELDS)
        ]

    def get_stats(self, collection: str) -> dict:
        data: list[dict] = self.get_dataset(collection)
        poets:  dict[str, int] = {}
        topics: dict[str, int] = {}

        for poem in data:
            poet  = poem.get("poet",  "Unknown")
            topic = poem.get("topic", "Unknown")
            poets[poet]   = poets.get(poet, 0)   + 1
            topics[topic] = topics.get(topic, 0) + 1

        return {
            "collection":    collection,
            "total_poems":   len(data),
            "unique_poets":  len(poets),
            "unique_topics": len(topics),
            "top_5_poets":   sorted(poets.items(),  key=lambda x: x[1], reverse=True)[:5],
            "top_5_topics":  sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5],
        }


# ---------------------------------------------------------------------------
# 3. Singleton — import `db` everywhere
# ---------------------------------------------------------------------------

db = TamilLiteratureDB()