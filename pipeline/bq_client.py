"""BigQuery client singleton for pipeline."""
from google.cloud import bigquery
from config import PROJECT_ID, DATASET

_client: bigquery.Client | None = None


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def table_ref(table_name: str) -> str:
    return f"{PROJECT_ID}.{DATASET}.{table_name}"


def run_query(sql: str, params: list | None = None) -> list[dict]:
    client = get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    result = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in result]


def insert_rows(table_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    client = get_client()
    errors = client.insert_rows_json(table_ref(table_name), rows)
    if errors:
        raise RuntimeError(f"BQ insert errors in {table_name}: {errors}")
