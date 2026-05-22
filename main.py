"""
main.py — App entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Register middleware
  - Mount routers
  - Root health/overview endpoint

Nothing else. All data logic lives in database.py, all routes in router.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import db
from router import router as literature_router


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tamil Sangam Literature API",
    description=(
        "REST API for Sangam-era Tamil literature — Narrinai, Kurunthogai, Ainkurunuru, "
        "and future collections. Add a new dataset by editing one dictionary in database.py."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(literature_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"], summary="API status and collection overview")
def home():
    """
    Returns API health status and a live count of poems per loaded collection.
    """
    return {
        "status": "ok",
        "message": "Tamil Sangam Literature API is running.",
        "collections": {
            name: len(data)
            for name, data in db.datasets.items()
        },
        "docs": "/docs",
    }
