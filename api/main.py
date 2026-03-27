"""Prisme FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import catalog, products, anomalies, search, reports, quality

app = FastAPI(title="Prisme API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(products.router)
app.include_router(anomalies.router)
app.include_router(search.router)
app.include_router(reports.router)
app.include_router(quality.router)


@app.get("/health")
def health():
    return {"status": "ok"}
