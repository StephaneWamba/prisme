"""Vertex AI Gemini wrapper for on-demand report generation."""
import json
import logging

import vertexai
from vertexai.generative_models import GenerativeModel

from config import PROJECT_ID, VERTEX_LOCATION, VERTEX_MODEL

logger = logging.getLogger(__name__)

_initialized = False


def _init():
    global _initialized
    if not _initialized:
        vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)
        _initialized = True


def generate_report_from_context(context: dict) -> dict:
    _init()
    model = GenerativeModel(VERTEX_MODEL)

    prompt = f"""Tu es un expert en qualite catalogue retail/FMCG.
Genere un rapport JSON sur la qualite du catalogue.

Contexte:
{json.dumps(context, indent=2, ensure_ascii=False)}

Reponds UNIQUEMENT avec un objet JSON valide:
{{
  "executive_summary": "string",
  "critical_issues": ["string"],
  "worst_categories": ["string"],
  "recommendations": ["string"]
}}"""

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        logger.error(f"Vertex AI error: {e}")
        return {
            "executive_summary": "Rapport indisponible.",
            "critical_issues": [],
            "worst_categories": [],
            "recommendations": [],
        }
