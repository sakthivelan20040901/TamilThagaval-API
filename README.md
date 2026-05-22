# Tamil Sangam Literature API

REST API for Sangam-era Tamil poetry — Narrinai, Kurunthogai, Ainkurunuru, and future collections.

---

## Project Structure

```
tamil_api/
├── main.py        # App factory, middleware, root endpoint
├── database.py    # Dataset loader, transformer, query engine
├── router.py      # All API route definitions
└── README.md
```

---

## Running the API

```bash
pip install fastapi uvicorn

uvicorn main:app --reload
```

Swagger UI → http://localhost:8000/docs

---

## API Endpoints

All endpoints follow the pattern `/api/{collection}/...`

Valid collection names: `narrinai`, `kurunthogai`, `ainkurunuru`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check + poem counts |
| GET | `/api/{collection}` | All poems |
| GET | `/api/{collection}/random` | Random poem |
| GET | `/api/{collection}/search?q=...` | Full-text search |
| GET | `/api/{collection}/stats/summary` | Stats (poets, topics, counts) |
| GET | `/api/{collection}/topic/{topic_name}` | Filter by topic |
| GET | `/api/{collection}/poet/{poet_name}` | Filter by poet |
| GET | `/api/{collection}/{poem_number}` | Single poem by number |

---

## Adding a New Dataset

### Case 1 — Flat JSON (list of poems, no transformation needed)

Edit **only** `database.py`:

```python
DATASET_PATHS = {
    "narrinai":    "...",
    "kurunthogai": "...",
    "ainkurunuru": "...",
    "purananuru":  "/path/to/purananuru.json",  # ← add this line
}
```

Done. The new dataset is immediately available at `/api/purananuru/...`.

---

### Case 2 — Nested/grouped JSON (needs flattening)

Edit **only** `database.py`:

**Step 1** — Add the path:
```python
DATASET_PATHS = {
    ...
    "kalithogai": "/path/to/kalithogai.json",
}
```

**Step 2** — Register a transformer:
```python
DATASET_TRANSFORMS = {
    "ainkurunuru": "_transform_ainkurunuru",
    "kalithogai":  "_transform_kalithogai",   # ← add this
}
```

**Step 3** — Write the transformer method inside `TamilLiteratureDB`:
```python
def _transform_kalithogai(self, raw: list[dict]) -> list[dict]:
    # raw is whatever your JSON looks like
    flattened = []
    for section in raw:
        for poem in section.get("verses", []):
            poem["topic"] = section.get("title", "")
            flattened.append(poem)
    return flattened
```

No changes to `router.py` or `main.py` — ever.

---

## Search Fields

Full-text search (`/search?q=...`) covers:

- `poem` — the Tamil verse
- `poet` — poet name
- `topic` — akam/puram category
- `note` — editorial notes
- `explanation` — commentary
- `mudippu` — conclusion/summary
- `karuthu` — central theme/idea
