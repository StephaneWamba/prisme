"""GET /anomalies"""
from fastapi import APIRouter

from services import bigquery as bq

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("")
def list_anomalies(
    type: str | None = None,
    severity: str | None = None,
    limit: int = 50,
):
    return bq.get_anomalies(type_filter=type, severity=severity, limit=limit)
