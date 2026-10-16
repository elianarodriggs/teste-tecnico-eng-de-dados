from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Any

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def extraction_date() -> str:
    return os.environ.get("EXTRACTION_DATE") or date.today().isoformat()


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "admin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "change-me"),
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
    )


def bucket_name() -> str:
    return os.environ.get("S3_BUCKET", "lake")


def ensure_bucket(attempts: int = 15):
    client = s3_client()
    name = bucket_name()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            try:
                client.head_bucket(Bucket=name)
            except ClientError:
                logger.info("criando bucket %s", name)
                client.create_bucket(Bucket=name)
            return client
        except Exception as exc:
            last_error = exc
            logger.warning("storage indisponível (%s); tentativa %s/%s", exc, attempt, attempts)
            time.sleep(2)
    raise RuntimeError("não foi possível acessar o storage S3") from last_error


def put_bytes(key: str, payload: bytes, content_type: str) -> None:
    s3_client().put_object(Bucket=bucket_name(), Key=key, Body=payload, ContentType=content_type)


def put_json(key: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    put_bytes(key, body, "application/json")


def get_bytes(key: str) -> bytes:
    response = s3_client().get_object(Bucket=bucket_name(), Key=key)
    return response["Body"].read()


def put_parquet(key: str, frame: pd.DataFrame) -> None:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    put_bytes(key, buffer.getvalue(), "application/octet-stream")


def read_parquet(key: str) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(get_bytes(key)))


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def manifest(**fields: Any) -> dict[str, Any]:
    payload = {"extracted_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    payload.update(fields)
    return payload
