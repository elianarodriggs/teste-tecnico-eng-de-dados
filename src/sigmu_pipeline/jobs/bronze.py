from __future__ import annotations

import logging

from sigmu_pipeline.config import PipelineConfig, object_prefix
from sigmu_pipeline.csv_source import download_csv
from sigmu_pipeline.io import ensure_bucket, lineage_manifest, put_bytes, put_json, sha256

logger = logging.getLogger(__name__)


def run_bronze(cfg: PipelineConfig) -> dict:
    """Landing fiel: bytes do C3SL, sem parsing.

    Equivale à camada raw: o objeto de origem é preservado e a
    transformação fica para a curated (Silver).
    """
    ensure_bucket(cfg.s3)
    summary: dict = {"snapshot_date": cfg.snapshot_date, "tables": {}}

    for table_name, meta in cfg.tables.items():
        url = cfg.base_url + meta["file"]
        prefix = object_prefix("bronze", table_name, cfg.snapshot_date)
        logger.info("bronze %s <- %s", table_name, url)
        payload = download_csv(url)
        data_key = f"{prefix}/data.csv"
        put_bytes(cfg.s3, data_key, payload, "text/csv")
        manifest = lineage_manifest(
            layer="bronze",
            table=table_name,
            source_url=url,
            source_file=meta["file"],
            snapshot_date=cfg.snapshot_date,
            bytes=len(payload),
            sha256=sha256(payload),
            object_key=data_key,
        )
        put_json(cfg.s3, f"{prefix}/_manifest.json", manifest)
        put_bytes(cfg.s3, f"{prefix}/_SUCCESS", b"", "text/plain")
        summary["tables"][table_name] = {"bytes": len(payload), "key": data_key}

    return summary
