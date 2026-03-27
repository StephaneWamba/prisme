"""GET /catalog/health, GET /categories"""
from fastapi import APIRouter

from services import bigquery as bq

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/health")
def catalog_health():
    health = bq.get_catalog_health()
    evolution = bq.get_score_evolution()
    return {"health": health, "evolution": evolution}


@router.get("/categories")
def categories(limit: int = 50):
    return bq.get_categories(limit=limit)
