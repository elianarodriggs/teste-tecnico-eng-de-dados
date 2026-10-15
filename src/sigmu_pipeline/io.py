from __future__ import annotations

import hashlib
import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import boto3
import pandas as pd
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from sigmu_pipeline.config import S3Config

logger = logging.getLogger(__name__)


def s3_client(cfg: S3Config) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=cfg.endpoint_url,
        aws_access_key_id=cfg.access_key,
        aws_secret_access_key=cfg.secret_key,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
    )


def ensure_bucket(cfg: S3Config, attempts: int = 15) -> BaseClient:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            client = s3_client(cfg)
            try:
                client.head_bucket(Bucket=cfg.bucket)
            except ClientError:
                logger.info("criando bucket %s", cfg.bucket)
                client.create_bucket(Bucket=cfg.bucket)
            return client
        except Exception as exc:  # storage ainda subindo
            last_error = exc
            logger.warning("storage indisponível (%s); tentativa %s/%s", exc, attempt, attempts)
            time.sleep(2)
    raise RuntimeError("não foi possível acessar o storage S3") from last_error


def put_bytes(cfg: S3Config, key: str, payload: bytes, content_type: str) -> None:
    client = s3_client(cfg)
    client.put_object(Bucket=cfg.bucket, Key=key, Body=payload, ContentType=content_type)


def put_json(cfg: S3Config, key: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    put_bytes(cfg, key, body, "application/json")


def get_bytes(cfg: S3Config, key: str) -> bytes:
    client = s3_client(cfg)
    response = client.get_object(Bucket=cfg.bucket, Key=key)
    return response["Body"].read()


def write_parquet(cfg: S3Config, key: str, frame: pd.DataFrame) -> None:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    put_bytes(cfg, key, buffer.getvalue(), "application/octet-stream")


def read_parquet(cfg: S3Config, key: str) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(get_bytes(cfg, key)))


def lineage_manifest(**fields: Any) -> dict[str, Any]:
    manifest = {
        "extracted_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    manifest.update(fields)
    return manifest


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
