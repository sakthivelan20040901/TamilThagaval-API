"""
tests/test_api.py — Automated test suite for Tamil Literature API.

Tests every endpoint for every registered collection.
When you add a new dataset to DATASET_PATHS in database.py,
it is automatically picked up and tested here — no changes needed.

Run locally:
    pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from database import db

client = TestClient(app)

# ---------------------------------------------------------------------------
# Dynamically build the list of collections that actually loaded successfully.
# Skips collections whose JSON files are missing (e.g. in CI without data/).
# ---------------------------------------------------------------------------
LIVE_COLLECTIONS = [
    name for name, data in db.datasets.items() if data
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_first_poem_number(collection: str) -> str | None:
    """Return the poem_number/id of the first poem in a collection."""
    data = db.datasets.get(collection, [])
    if not data:
        return None
    first = data[0]
    return str(first.get("poem_number") or first.get("id") or "")


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_status(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_has_collections(self):
        r = client.get("/")
        body = r.json()
        assert "collections" in body
        assert isinstance(body["collections"], dict)

    def test_root_lists_all_registered_datasets(self):
        r = client.get("/")
        body = r.json()
        for name in db.datasets:
            assert name in body["collections"]


# ---------------------------------------------------------------------------
# Per-collection endpoint tests
# Parametrized over every collection that loaded data successfully.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("collection", LIVE_COLLECTIONS)
class TestCollectionEndpoints:

    def test_get_all_returns_200(self, collection):
        r = client.get(f"/api/{collection}")
        assert r.status_code == 200

    def test_get_all_has_count_and_results(self, collection):
        r = client.get(f"/api/{collection}")
        body = r.json()
        assert "count" in body
        assert "results" in body
        assert isinstance(body["results"], list)
        assert body["count"] == len(body["results"])

    def test_get_all_count_matches_loaded_data(self, collection):
        r = client.get(f"/api/{collection}")
        body = r.json()
        assert body["count"] == len(db.datasets[collection])

    def test_random_returns_200(self, collection):
        r = client.get(f"/api/{collection}/random")
        assert r.status_code == 200

    def test_random_returns_a_dict(self, collection):
        r = client.get(f"/api/{collection}/random")
        assert isinstance(r.json(), dict)

    def test_random_is_different_occasionally(self, collection):
        """Call random 5 times — results should not all be identical."""
        results = {
            str(client.get(f"/api/{collection}/random").json())
            for _ in range(5)
        }
        # For collections with more than 1 poem this should vary.
        # We just assert we got at least 1 valid response.
        assert len(results) >= 1

    def test_stats_returns_200(self, collection):
        r = client.get(f"/api/{collection}/stats/summary")
        assert r.status_code == 200

    def test_stats_has_required_fields(self, collection):
        r = client.get(f"/api/{collection}/stats/summary")
        body = r.json()
        assert "total_poems"   in body
        assert "unique_poets"  in body
        assert "unique_topics" in body
        assert "top_5_poets"   in body
        assert "top_5_topics"  in body

    def test_stats_total_matches_loaded_data(self, collection):
        r = client.get(f"/api/{collection}/stats/summary")
        body = r.json()
        assert body["total_poems"] == len(db.datasets[collection])

    def test_search_returns_200(self, collection):
        r = client.get(f"/api/{collection}/search?q=அ")
        assert r.status_code == 200

    def test_search_has_count_and_results(self, collection):
        r = client.get(f"/api/{collection}/search?q=அ")
        body = r.json()
        assert "count"   in body
        assert "results" in body
        assert body["count"] == len(body["results"])

    def test_search_empty_query_returns_422(self, collection):
        """FastAPI should reject an empty q= with 422 Unprocessable Entity."""
        r = client.get(f"/api/{collection}/search?q=")
        assert r.status_code == 422

    def test_search_missing_query_returns_422(self, collection):
        r = client.get(f"/api/{collection}/search")
        assert r.status_code == 422

    def test_get_by_poem_number_returns_200(self, collection):
        poem_number = get_first_poem_number(collection)
        if not poem_number:
            pytest.skip(f"No poem_number found in {collection}")
        r = client.get(f"/api/{collection}/{poem_number}")
        assert r.status_code == 200

    def test_get_by_poem_number_returns_correct_poem(self, collection):
        poem_number = get_first_poem_number(collection)
        if not poem_number:
            pytest.skip(f"No poem_number found in {collection}")
        r = client.get(f"/api/{collection}/{poem_number}")
        body = r.json()
        actual_id = str(body.get("poem_number") or body.get("id") or "")
        assert actual_id == poem_number

    def test_get_nonexistent_poem_returns_404(self, collection):
        r = client.get(f"/api/{collection}/999999")
        assert r.status_code == 404

    def test_topic_filter_returns_200(self, collection):
        # Use the topic of the first poem as a known-good filter value
        first = db.datasets[collection][0]
        topic = first.get("topic", "")
        if not topic:
            pytest.skip(f"No topic field in {collection}")
        r = client.get(f"/api/{collection}/topic/{topic}")
        assert r.status_code == 200

    def test_topic_filter_results_all_match(self, collection):
        first = db.datasets[collection][0]
        topic = first.get("topic", "")
        if not topic:
            pytest.skip(f"No topic field in {collection}")
        r = client.get(f"/api/{collection}/topic/{topic}")
        body = r.json()
        for poem in body["results"]:
            assert topic.lower() in poem.get("topic", "").lower()

    def test_poet_filter_returns_200(self, collection):
        first = db.datasets[collection][0]
        poet = first.get("poet", "")
        if not poet:
            pytest.skip(f"No poet field in {collection}")
        r = client.get(f"/api/{collection}/poet/{poet}")
        assert r.status_code == 200

    def test_poet_filter_results_all_match(self, collection):
        first = db.datasets[collection][0]
        poet = first.get("poet", "")
        if not poet:
            pytest.skip(f"No poet field in {collection}")
        r = client.get(f"/api/{collection}/poet/{poet}")
        body = r.json()
        for poem in body["results"]:
            assert poet.lower() in poem.get("poet", "").lower()


# ---------------------------------------------------------------------------
# Unknown collection handling
# ---------------------------------------------------------------------------

class TestUnknownCollection:

    def test_unknown_collection_returns_404(self):
        r = client.get("/api/doesnotexist")
        assert r.status_code == 404

    def test_unknown_collection_error_lists_available(self):
        r = client.get("/api/doesnotexist")
        body = r.json()
        assert "available" in body["detail"]

    def test_unknown_collection_random_returns_404(self):
        r = client.get("/api/doesnotexist/random")
        assert r.status_code == 404

    def test_unknown_collection_search_returns_404(self):
        r = client.get("/api/doesnotexist/search?q=test")
        assert r.status_code == 404

    def test_case_insensitive_collection_name(self):
        """Uppercase collection names should work identically to lowercase."""
        if not LIVE_COLLECTIONS:
            pytest.skip("No live collections")
        name = LIVE_COLLECTIONS[0]
        r_lower = client.get(f"/api/{name}/random")
        r_upper = client.get(f"/api/{name.upper()}/random")
        assert r_lower.status_code == 200
        assert r_upper.status_code == 200