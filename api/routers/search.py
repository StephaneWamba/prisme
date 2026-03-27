"""POST /search/visual - visual similarity search via CLIP + BigQuery VECTOR_SEARCH"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import bigquery as bq
from services import clip

router = APIRouter(prefix="/search", tags=["search"])


class VisualSearchRequest(BaseModel):
    image_url: str
    top_k: int = 10


@router.post("/visual")
def visual_search(body: VisualSearchRequest):
    try:
        embedding = clip.encode_image_url(body.image_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image unavailable: {e}")

    similar = bq.vector_search(embedding, top_k=body.top_k)

    # Enrich with product metadata
    eans = [r["ean"] for r in similar]
    if not eans:
        return []

    products = {
        p["ean"]: p
        for p in bq.query(
            f"""
            SELECT ean, product_name, categories, catalog_score, thumbnail_url_128
            FROM `prisme-wamba-2026.prisme_dataset.product_scores`
            WHERE ean IN UNNEST(@eans) AND run_date = (SELECT MAX(run_date) FROM `prisme-wamba-2026.prisme_dataset.product_scores`)
            """,
            [bq.bigquery.ArrayQueryParameter("eans", "STRING", eans)],
        )
    }

    return [
        {
            **r,
            "product_name": products.get(r["ean"], {}).get("product_name"),
            "categories": products.get(r["ean"], {}).get("categories"),
            "thumbnail_url": products.get(r["ean"], {}).get("thumbnail_url_128"),
            "catalog_score": products.get(r["ean"], {}).get("catalog_score"),
        }
        for r in similar
    ]
