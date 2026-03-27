"""
Ingest Open Food Facts data via their public API.
Fetches French products with images, loads ~10k into products_selected.

Usage: python ingest_off.py
"""
import asyncio
import logging
import time
from datetime import datetime, timezone

import aiohttp
import bq_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
TARGET_PRODUCTS = 10_000
PAGE_SIZE = 1000  # OFF API max per page
CONCURRENT_PAGES = 4


def _parse_product(p: dict) -> dict | None:
    image_url = p.get("image_url") or p.get("image_front_url")
    product_name = (p.get("product_name_fr") or p.get("product_name") or "").strip()
    ean = p.get("code", "").strip()

    if not image_url or not product_name or not ean:
        return None

    return {
        "ean": ean,
        "product_name": product_name[:500],
        "brands": (p.get("brands") or "")[:200],
        "categories": (p.get("categories") or p.get("categories_tags", [""])[0] or "")[:500],
        "ingredients_text": (p.get("ingredients_text_fr") or p.get("ingredients_text") or "")[:2000],
        "nutriscore_grade": (p.get("nutriscore_grade") or "").strip()[:1] or None,
        "quantity": (p.get("quantity") or "")[:100],
        "packaging": (p.get("packaging") or "")[:200],
        "image_url": image_url[:1000],
        "image_small_url": (p.get("image_small_url") or "")[:1000] or None,
        "country_code": "FR",
        "last_modified_t": datetime.utcfromtimestamp(p.get("last_modified_t", 0)).isoformat() + "Z"
            if p.get("last_modified_t") else None,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_page(session: aiohttp.ClientSession, page: int, semaphore: asyncio.Semaphore) -> list[dict]:
    async with semaphore:
        params = {
            "action": "process",
            "tagtype_0": "countries",
            "tag_contains_0": "contains",
            "tag_0": "france",
            "tagtype_1": "states",
            "tag_contains_1": "contains",
            "tag_1": "en:photos-uploaded",
            "json": "1",
            "page_size": PAGE_SIZE,
            "page": page,
            "fields": "code,product_name,product_name_fr,brands,categories,categories_tags,"
                      "ingredients_text,ingredients_text_fr,nutriscore_grade,quantity,packaging,"
                      "image_url,image_front_url,image_small_url,last_modified_t",
            "sort_by": "last_modified_t",
        }
        try:
            async with session.get(OFF_SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    logger.warning(f"Page {page}: HTTP {resp.status}")
                    return []
                data = await resp.json(content_type=None)
                products = data.get("products", [])
                parsed = [p for p in (_parse_product(x) for x in products) if p]
                logger.info(f"Page {page}: {len(products)} raw -> {len(parsed)} valid")
                return parsed
        except Exception as e:
            logger.error(f"Page {page} failed: {e}")
            return []


async def ingest(target: int = TARGET_PRODUCTS) -> int:
    # Check existing count
    existing = bq_client.run_query(
        "SELECT COUNT(*) AS n FROM `prisme-wamba-2026.prisme_dataset.products_selected`"
    )
    if existing and existing[0].get("n", 0) > 0:
        logger.info(f"Already have {existing[0]['n']} products, skipping ingest.")
        return existing[0]["n"]

    semaphore = asyncio.Semaphore(CONCURRENT_PAGES)
    all_products: list[dict] = []
    seen_eans: set[str] = set()
    page = 1

    connector = aiohttp.TCPConnector(limit=CONCURRENT_PAGES)
    async with aiohttp.ClientSession(connector=connector) as session:
        while len(all_products) < target:
            # Fetch a batch of pages
            batch_pages = list(range(page, page + CONCURRENT_PAGES))
            tasks = [fetch_page(session, p, semaphore) for p in batch_pages]
            results = await asyncio.gather(*tasks)

            new_this_batch = 0
            for products in results:
                for p in products:
                    if p["ean"] not in seen_eans:
                        seen_eans.add(p["ean"])
                        all_products.append(p)
                        new_this_batch += 1

            logger.info(f"Total collected: {len(all_products)}/{target}")

            if new_this_batch == 0:
                logger.info("No more products, stopping.")
                break

            page += CONCURRENT_PAGES

            # Write batch to BQ every 2000 products
            if len(all_products) >= 2000 or len(all_products) >= target:
                to_write = all_products[:target]
                chunk_size = 500
                for i in range(0, len(to_write), chunk_size):
                    bq_client.insert_rows("products_selected", to_write[i:i+chunk_size])
                    logger.info(f"Wrote rows {i} to {min(i+chunk_size, len(to_write))}")
                return len(to_write)

            await asyncio.sleep(1)  # polite delay

    return 0


def run():
    n = asyncio.run(ingest())
    logger.info(f"Ingestion complete: {n} products loaded.")
    return n


if __name__ == "__main__":
    run()
