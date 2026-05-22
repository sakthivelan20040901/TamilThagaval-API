"""
router.py — All literature collection endpoints.

Uses {collection} as a route-level path parameter (not a prefix parameter,
which FastAPI does not parse reliably). Adding a new dataset requires zero
changes here — just update DATASET_PATHS in database.py.
"""

import random
from fastapi import APIRouter, HTTPException, Query, Path
from database import db

router = APIRouter(
    prefix="/api",
    tags=["Literature Collections"],
)

# ---------------------------------------------------------------------------
# Shared path annotation (keeps every route DRY)
# ---------------------------------------------------------------------------

CollectionParam = Path(
    ...,
    description="Dataset name: narrinai | kurunthogai | ainkurunuru (or any future collection)",
    example="narrinai",
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{collection}",
    summary="All poems in a collection",
    description="Returns every poem in the specified collection.",
)
def get_all_poems(collection: str = CollectionParam):
    data = db.get_all(collection)
    return {"collection": collection, "count": len(data), "results": data}


@router.get(
    "/{collection}/random",
    summary="Random poem",
    description="Returns a single randomly selected poem.",
)
def get_random_poem(collection: str = CollectionParam):
    return db.get_random(collection)


@router.get(
    "/{collection}/search",
    summary="Full-text search",
    description=(
        "Searches poem text, poet name, topic, note, explanation, mudippu, and karuthu fields."
    ),
)
def search_collection(
    collection: str = CollectionParam,
    q: str = Query(..., min_length=1, description="Search term"),
):
    results = db.search(collection, q)
    return {"collection": collection, "query": q, "count": len(results), "results": results}


@router.get(
    "/{collection}/stats/summary",
    summary="Collection statistics",
    description="Returns poem count, unique poets/topics, and top-5 rankings.",
)
def get_stats(collection: str = CollectionParam):
    return db.get_stats(collection)


@router.get(
    "/{collection}/topic/{topic_name}",
    summary="Filter by topic",
    description="Returns all poems whose topic field contains the given value.",
)
def get_by_topic(
    collection: str = CollectionParam,
    topic_name: str = Path(..., description="Topic name to filter by"),
):
    results = db.filter_by_field(collection, "topic", topic_name)
    return {"collection": collection, "topic": topic_name, "count": len(results), "results": results}


@router.get(
    "/{collection}/poet/{poet_name}",
    summary="Filter by poet",
    description="Returns all poems attributed to a given poet.",
)
def get_by_poet(
    collection: str = CollectionParam,
    poet_name: str = Path(..., description="Poet name to filter by"),
):
    results = db.filter_by_field(collection, "poet", poet_name)
    return {"collection": collection, "poet": poet_name, "count": len(results), "results": results}


@router.get(
    "/{collection}/{poem_number}",
    summary="Single poem by number",
    description="Returns one poem by its poem_number (or id) field.",
)
def get_poem_by_number(
    collection: str = CollectionParam,
    poem_number: int = Path(..., description="The poem number", ge=1),
):
    result = db.find_by_number(collection, poem_number)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Poem {poem_number} not found in '{collection}'.",
        )
    return result
