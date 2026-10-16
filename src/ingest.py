import logging
import time

import requests

from sources import BASE_URL, DATASET_PERIOD, TABLES
from storage import ensure_bucket, extraction_date, manifest, put_bytes, put_json, sha256

logger = logging.getLogger(__name__)


def bronze_key(table, when, filename):
    return f"bronze/{table}/extraction_date={when}/{filename}"


def download(url, attempts=3):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            if not response.content:
                raise RuntimeError(f"arquivo vazio: {url}")
            return response.content
        except Exception as exc:
            last_error = exc
            logger.warning("falha ao baixar %s (%s); tentativa %s/%s", url, exc, attempt, attempts)
            time.sleep(2)
    raise RuntimeError(f"não foi possível baixar {url}") from last_error


def run_ingest():
    ensure_bucket()
    when = extraction_date()
    summary = {"extraction_date": when, "dataset_period": DATASET_PERIOD, "tables": {}}

    for table in TABLES:
        url = BASE_URL + table["file"]
        logger.info("bronze %s <- %s", table["name"], url)
        try:
            payload = download(url)
        except Exception:
            if table["required"]:
                raise
            logger.exception("fonte opcional indisponível: %s", table["name"])
            summary["tables"][table["name"]] = {"status": "failed_optional"}
            continue

        key = bronze_key(table["name"], when, table["file"])
        put_bytes(key, payload, "text/csv")
        meta = manifest(
            layer="bronze",
            table=table["name"],
            source_url=url,
            source_file=table["file"],
            extraction_date=when,
            dataset_period=DATASET_PERIOD,
            bytes=len(payload),
            sha256=sha256(payload),
            object_key=key,
            required=table["required"],
        )
        put_json(f"bronze/{table['name']}/extraction_date={when}/_manifest.json", meta)
        summary["tables"][table["name"]] = {
            "bytes": len(payload),
            "key": key,
            "sha256": meta["sha256"],
        }

    return summary
