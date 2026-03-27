"""GET /products, GET /products/{ean}, POST /products/audit"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import bigquery as bq

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(
    page: int = 1,
    per_page: int = 30,
    min_score: int | None = None,
    max_score: int | None = None,
    category: str | None = None,
):
    return bq.get_products(
        page=page,
        per_page=per_page,
        min_score=min_score,
        max_score=max_score,
        category=category,
    )


@router.get("/{ean}")
def product_detail(ean: str):
    product = bq.get_product_detail(ean)
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouve")
    return product


class AuditRequest(BaseModel):
    ean: str


@router.post("/audit")
def audit_product(body: AuditRequest):
    """On-demand text + visual audit for a single product."""
    product = bq.get_product_detail(body.ean)
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouve")
    return {
        "ean": body.ean,
        "product": product,
        "audit": {
            "text_score": product.get("text_score"),
            "visual_score": product.get("visual_score"),
            "catalog_score": product.get("catalog_score"),
            "resolution": product.get("resolution_score"),
            "sharpness": product.get("sharpness_score"),
            "centration": product.get("centration_score"),
            "object_label": product.get("primary_object_label"),
        },
    }
