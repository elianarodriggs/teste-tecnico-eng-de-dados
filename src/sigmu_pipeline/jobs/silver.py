from __future__ import annotations

import logging

from sigmu_pipeline.config import PipelineConfig, object_prefix
from sigmu_pipeline.csv_source import parse_sigmu_csv
from sigmu_pipeline.io import get_bytes, lineage_manifest, put_bytes, put_json, write_parquet
from sigmu_pipeline.quality import apply_types, deduplicate

logger = logging.getLogger(__name__)


def run_silver(cfg: PipelineConfig) -> dict:
    """Curadoria: encoding, tipos, nulos e deduplicação.

    Equivale aos modelos da camada curated: uma tabela tipada por fonte,
    ainda no grão de origem, pronta para o join da Gold.
    """
    summary: dict = {"snapshot_date": cfg.snapshot_date, "tables": {}}

    for table_name, meta in cfg.tables.items():
        bronze_key = f"{object_prefix('bronze', table_name, cfg.snapshot_date)}/data.csv"
        logger.info("silver %s <- %s", table_name, bronze_key)
        raw = get_bytes(cfg.s3, bronze_key)
        frame, dropped_parse = parse_sigmu_csv(raw)
        rows_parsed = len(frame)
        frame = apply_types(table_name, frame)
        frame, null_keys, duplicates = deduplicate(frame, list(meta.get("primary_key") or []))

        prefix = object_prefix("silver", table_name, cfg.snapshot_date)
        data_key = f"{prefix}/data.parquet"
        write_parquet(cfg.s3, data_key, frame)
        manifest = lineage_manifest(
            layer="silver",
            table=table_name,
            snapshot_date=cfg.snapshot_date,
            source_object=bronze_key,
            object_key=data_key,
            rows_parsed=rows_parsed,
            rows_dropped_parse=dropped_parse,
            rows_dropped_null_key=null_keys,
            rows_dropped_duplicate=duplicates,
            rows_out=len(frame),
            primary_key=list(meta.get("primary_key") or []),
        )
        put_json(cfg.s3, f"{prefix}/_manifest.json", manifest)
        put_bytes(cfg.s3, f"{prefix}/_SUCCESS", b"", "text/plain")
        summary["tables"][table_name] = {
            "rows_out": len(frame),
            "rows_dropped_parse": dropped_parse,
            "rows_dropped_duplicate": duplicates,
            "rows_dropped_null_key": null_keys,
        }
        logger.info("silver %s: %s", table_name, summary["tables"][table_name])

    return summary
