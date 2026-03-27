"""Download product images from image_url, store to GCS originals."""
import asyncio
import gc
import logging
from io import BytesIO

import aiohttp
from google.cloud import storage

from config import (
    GCS_BUCKET,
    GCS_ORIGINALS_PREFIX,
    DOWNLOAD_CONCURRENT,
    DOWNLOAD_TIMEOUT,
    DOWNLOAD_RETRY,
    DOWNLOAD_MIN_SIZE_KB,
)

logger = logging.getLogger(__name__)


def _gcs_client() -> storage.Client:
    return storage.Client()


def _gcs_path(ean: str) -> str:
    return f"{GCS_ORIGINALS_PREFIX}/{ean}.jpg"


async def _download_one(
    session: aiohttp.ClientSession,
    ean: str,
    image_url: str,
    bucket: storage.Bucket,
    semaphore: asyncio.Semaphore,
) -> dict:
    async with semaphore:
        for attempt in range(DOWNLOAD_RETRY):
            try:
                async with session.get(
                    image_url,
                    timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT),
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        return {"ean": ean, "success": False, "error": f"HTTP {resp.status}"}
                    data = await resp.read()
                    size_kb = len(data) / 1024
                    if size_kb < DOWNLOAD_MIN_SIZE_KB:
                        return {"ean": ean, "success": False, "error": f"image too small ({size_kb:.1f}KB)"}
                    blob = bucket.blob(_gcs_path(ean))
                    blob.upload_from_file(BytesIO(data), content_type="image/jpeg")
                    return {"ean": ean, "success": True, "error": None, "size_kb": size_kb}
            except Exception as e:
                if attempt == DOWNLOAD_RETRY - 1:
                    return {"ean": ean, "success": False, "error": str(e)}
                await asyncio.sleep(1)
    return {"ean": ean, "success": False, "error": "max retries"}


async def download_all(products: list[dict]) -> list[dict]:
    """Download images for all products. Returns list of result dicts."""
    gcs = _gcs_client()
    bucket = gcs.bucket(GCS_BUCKET)
    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENT)
    connector = aiohttp.TCPConnector(limit=DOWNLOAD_CONCURRENT)
    results = []

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            _download_one(session, p["ean"], p["image_url"], bucket, semaphore)
            for p in products
            if p.get("image_url")
        ]
        chunk_size = 500
        for i in range(0, len(tasks), chunk_size):
            chunk_results = await asyncio.gather(*tasks[i : i + chunk_size])
            results.extend(chunk_results)
            gc.collect()
            logger.info(f"Downloaded {min(i + chunk_size, len(tasks))}/{len(tasks)}")

    ok = sum(1 for r in results if r["success"])
    logger.info(f"Download complete: {ok}/{len(results)} success")
    return results


def run(products: list[dict]) -> list[dict]:
    return asyncio.run(download_all(products))
