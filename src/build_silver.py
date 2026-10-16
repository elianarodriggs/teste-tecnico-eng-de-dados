from __future__ import annotations

import logging

import pandas as pd

from ingest import bronze_key
from parse_csv import apply_types, deduplicate, parse_csv
from sources import DATASET_PERIOD, TABLES
from storage import extraction_date, get_bytes, manifest, put_json, put_parquet

logger = logging.getLogger(__name__)


def silver_key(table: str, when: str) -> str:
    return f"silver/{table}/extraction_date={when}/data.parquet"


def run_silver() -> dict:
    when = extraction_date()
    metrics_rows = []
    quarantine_frames = []

    for table in TABLES:
        raw_key = bronze_key(table["name"], when, table["file"])
        logger.info("silver %s <- %s", table["name"], raw_key)
        try:
            raw = get_bytes(raw_key)
        except Exception:
            if table["required"]:
                raise
            logger.exception("bronze opcional ausente: %s", table["name"])
            continue

        frame, quarantine, parse_info = parse_csv(raw)
        rows_read = len(frame) + len(quarantine)
        frame, type_metrics = apply_types(table["name"], frame)
        null_key_rows = pd.DataFrame()
        if table["primary_key"]:
            missing = frame[table["primary_key"]].isna().any(axis=1)
            if missing.any():
                null_key_rows = frame.loc[missing].copy()
                null_key_rows.insert(0, "reason", "chave_nula")
                null_key_rows.insert(0, "table", table["name"])
        frame, dup_metrics = deduplicate(frame, table["primary_key"])

        out_key = silver_key(table["name"], when)
        put_parquet(out_key, frame)
        if not quarantine.empty:
            quarantine.insert(0, "table", table["name"])
            quarantine_frames.append(quarantine)
        if not null_key_rows.empty:
            quarantine_frames.append(null_key_rows)

        row = {
            "table": table["name"],
            "rows_input": rows_read,
            "rows_output": len(frame),
            "rows_rejected_parse": len(quarantine),
            "null_keys": dup_metrics["null_keys"],
            "exact_duplicates": dup_metrics["exact_duplicates"],
            "divergent_duplicates": dup_metrics["divergent_duplicates"],
            "null_bytes_removed": parse_info["null_bytes_removed"],
            "invalid_dates": type_metrics["invalid_dates"],
            "invalid_numbers": type_metrics["invalid_numbers"],
        }
        metrics_rows.append(row)
        put_json(
            f"silver/{table['name']}/extraction_date={when}/_manifest.json",
            manifest(
                layer="silver",
                table=table["name"],
                extraction_date=when,
                dataset_period=DATASET_PERIOD,
                source_object=raw_key,
                object_key=out_key,
                **{k: v for k, v in row.items() if k != "table"},
            ),
        )
        logger.info("silver %s: %s linhas", table["name"], len(frame))

    metrics = pd.DataFrame(metrics_rows)
    quality_prefix = f"silver/_quality/extraction_date={when}"
    put_parquet(f"{quality_prefix}/metrics.parquet", metrics)
    if quarantine_frames:
        rejected = pd.concat(quarantine_frames, ignore_index=True)
    else:
        rejected = pd.DataFrame(columns=["table", "line_number", "reason", "raw_line"])
    put_parquet(f"{quality_prefix}/quarentena.parquet", rejected)
    return {"extraction_date": when, "tables": metrics_rows, "rejected_rows": len(rejected)}
