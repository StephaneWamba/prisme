"""Generate daily Gemini report from BQ data and write to reports table."""
import json
import logging
import uuid
from datetime import datetime, timezone

import os

from google import genai

import bq_client

logger = logging.getLogger(__name__)


def _fetch_context() -> dict:
    """Fetch recent metrics and anomalies from BQ for Gemini prompt."""
    scores = bq_client.run_query(
        """
        WITH latest AS (SELECT MAX(run_date) AS max_run FROM `prisme-wamba-2026.prisme_dataset.product_scores`)
        SELECT
          ROUND(AVG(catalog_score), 1) AS avg_catalog,
          ROUND(AVG(text_score), 1) AS avg_text,
          ROUND(AVG(visual_score), 1) AS avg_visual,
          COUNT(*) AS n_products
        FROM `prisme-wamba-2026.prisme_dataset.product_scores`
        WHERE run_date = (SELECT max_run FROM latest)
        """
    )
    anomalies = bq_client.run_query(
        """
        SELECT metric_name, severity, description
        FROM `prisme-wamba-2026.prisme_dataset.text_anomalies`
        WHERE run_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END
        LIMIT 10
        """
    )
    worst_categories = bq_client.run_query(
        """
        WITH latest AS (SELECT MAX(run_date) AS max_run FROM `prisme-wamba-2026.prisme_dataset.product_scores`)
        SELECT
          TRIM(SPLIT(categories, ',')[SAFE_OFFSET(0)]) AS category,
          ROUND(AVG(catalog_score), 1) AS avg_score
        FROM `prisme-wamba-2026.prisme_dataset.product_scores`
        WHERE run_date = (SELECT max_run FROM latest)
        GROUP BY category
        ORDER BY avg_score ASC
        LIMIT 5
        """
    )
    return {
        "scores": scores[0] if scores else {},
        "anomalies": anomalies,
        "worst_categories": worst_categories,
    }


def _build_prompt(ctx: dict) -> str:
    s = ctx["scores"]
    return f"""Tu es un expert en qualite catalogue retail/FMCG.

Analyse les donnees d'audit qualite du catalogue Open Food Facts (France) ci-dessous
et genere un rapport JSON structure.

METRIQUES GLOBALES:
- Score catalogue: {s.get("avg_catalog", "N/A")}/100
- Score texte (metadonnees): {s.get("avg_text", "N/A")}/100
- Score visuel (assets): {s.get("avg_visual", "N/A")}/100
- Nombre de produits analyses: {s.get("n_products", "N/A")}

ANOMALIES DETECTEES (24h):
{json.dumps(ctx["anomalies"], indent=2, ensure_ascii=False)}

CATEGORIES LES PLUS DEGRADEES:
{json.dumps(ctx["worst_categories"], indent=2, ensure_ascii=False)}

Reponds UNIQUEMENT avec un objet JSON valide (pas de markdown, pas de texte autour):
{{
  "executive_summary": "3 phrases maximum pour un client retail non-technique",
  "catalog_score": {s.get("avg_catalog", 0)},
  "text_score": {s.get("avg_text", 0)},
  "visual_score": {s.get("avg_visual", 0)},
  "critical_issues": ["issue1", "issue2"],
  "worst_categories": ["cat1", "cat2", "cat3"],
  "recommendations": ["action1", "action2", "action3"]
}}"""


def generate(run_id: str, run_date: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    client = genai.Client(api_key=api_key)

    ctx = _fetch_context()
    prompt = _build_prompt(ctx)

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        parsed = {
            "executive_summary": "Rapport indisponible - erreur de generation.",
            "catalog_score": int(ctx["scores"].get("avg_catalog", 0) or 0),
            "text_score": int(ctx["scores"].get("avg_text", 0) or 0),
            "visual_score": int(ctx["scores"].get("avg_visual", 0) or 0),
            "critical_issues": [],
            "worst_categories": [],
            "recommendations": [],
        }
        raw = json.dumps(parsed)

    row = {
        "report_id": str(uuid.uuid4()),
        "report_date": run_date,
        "executive_summary": parsed.get("executive_summary", ""),
        "catalog_score": int(parsed.get("catalog_score", 0)),
        "text_score": int(parsed.get("text_score", 0)),
        "visual_score": int(parsed.get("visual_score", 0)),
        "critical_issues": json.dumps(parsed.get("critical_issues", []), ensure_ascii=False),
        "worst_categories": json.dumps(parsed.get("worst_categories", []), ensure_ascii=False),
        "recommendations": json.dumps(parsed.get("recommendations", []), ensure_ascii=False),
        "gemini_response_json": raw,
    }
    bq_client.insert_rows("reports", [row])
    logger.info("Report written to BQ")
    return parsed


def run(run_id: str, run_date: str) -> dict:
    return generate(run_id, run_date)
