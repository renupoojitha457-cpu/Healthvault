from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
import models
import os

from routes.routes_ai_analysis import router as ai_analysis_router

Base.metadata.create_all(bind=engine)

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HealthVault+ API", version="1.0.0")

# ── CORS: allow browser calls from any origin ─────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────
from routes.routes_auth import router as auth_router
from routes.routes_records import router as records_router
from routes.routes_metrics import router as metrics_router
from routes.routes_alerts import router as alerts_router
from routes.routes_analysis import router as analysis_router
from routes.routes_ai_analysis import router as ai_analysis_router
from routes.routes_extraction_test import router as extraction_test_router

app.include_router(auth_router,    prefix="/api/auth",    tags=["Auth"])
app.include_router(records_router, prefix="/api/records", tags=["Records"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(alerts_router,  prefix="/api/alerts",  tags=["Alerts"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(ai_analysis_router, prefix="/api/ai-analysis", tags=["AI Analysis"])
app.include_router(extraction_test_router, prefix="/api/extraction-test", tags=["Extraction Test"])


# Serve uploaded files as static
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "HealthVault+ API is running ✅", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}
