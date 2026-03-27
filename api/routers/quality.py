"""GET /quality/coverage, GET /quality/fields"""
from fastapi import APIRouter

from services import bigquery as bq

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/coverage")
def quality_coverage():
    return bq.get_quality_coverage()


@router.get("/fields")
def field_completeness():
    return bq.get_field_completeness()
