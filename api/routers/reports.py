"""GET /reports/latest, POST /reports/generate"""
import json

from fastapi import APIRouter, HTTPException

from services import bigquery as bq

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/latest")
def latest_report():
    report = bq.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="Aucun rapport disponible")

    # Parse JSON fields for cleaner response
    for field in ("critical_issues", "worst_categories", "recommendations"):
        val = report.get(field)
        if isinstance(val, str):
            try:
                report[field] = json.loads(val)
            except Exception:
                report[field] = []

    return report
