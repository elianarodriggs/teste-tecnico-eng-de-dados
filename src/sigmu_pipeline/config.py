from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class S3Config:
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str


@dataclass(frozen=True)
class PipelineConfig:
    s3: S3Config
    snapshot_date: str
    base_url: str
    tables: dict


def load_config() -> PipelineConfig:
    definitions = Path(os.environ.get("DEFINITIONS_PATH", repo_root() / "definitions" / "sources.yaml"))
    with definitions.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    s3 = S3Config(
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
        access_key=os.environ.get("S3_ACCESS_KEY", "admin"),
        secret_key=os.environ.get("S3_SECRET_KEY", "change-me"),
        bucket=os.environ.get("S3_BUCKET", "lake"),
    )
    return PipelineConfig(
        s3=s3,
        snapshot_date=str(raw["snapshot_date"]),
        base_url=str(raw["base_url"]),
        tables=dict(raw["tables"]),
    )


def object_prefix(layer: str, table: str, snapshot_date: str) -> str:
    return f"{layer}/{table}/snapshot_date={snapshot_date}"
