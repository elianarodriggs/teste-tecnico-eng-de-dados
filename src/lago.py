import io
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Lago:
    def __init__(self):
        self.bucket = os.environ.get("S3_BUCKET", "lake")
        self.data_extracao = os.environ.get("EXTRACTION_DATE") or date.today().isoformat()
        self.cliente = boto3.client(
            "s3",
            endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
            aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "admin"),
            aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "change-me"),
            region_name="us-east-1",
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
        )

    def garantir_bucket(self):
        ultimo_erro = None
        for tentativa in range(1, 16):
            try:
                self.cliente.head_bucket(Bucket=self.bucket)
                return
            except ClientError:
                pass
            except Exception as erro:
                ultimo_erro = erro
                logging.warning("storage indisponível (%s); tentativa %s/15", erro, tentativa)
                time.sleep(2)
                continue

            try:
                logging.info("criando bucket %s", self.bucket)
                self.cliente.create_bucket(Bucket=self.bucket)
                return
            except Exception as erro:
                ultimo_erro = erro
                logging.warning("storage indisponível (%s); tentativa %s/15", erro, tentativa)
                time.sleep(2)

        raise RuntimeError("não foi possível acessar o SeaweedFS") from ultimo_erro

    def gravar(self, caminho, conteudo, tipo):
        self.cliente.put_object(Bucket=self.bucket, Key=caminho, Body=conteudo, ContentType=tipo)

    def ler(self, caminho):
        resposta = self.cliente.get_object(Bucket=self.bucket, Key=caminho)
        return resposta["Body"].read()

    def gravar_parquet(self, caminho, tabela):
        buffer = io.BytesIO()
        tabela.to_parquet(buffer, index=False)
        self.gravar(caminho, buffer.getvalue(), "application/octet-stream")

    def ler_parquet(self, caminho):
        return pd.read_parquet(io.BytesIO(self.ler(caminho)))

    def gravar_json(self, caminho, dados):
        corpo = json.dumps(dados, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.gravar(caminho, corpo, "application/json")

    def manifesto(self, **campos):
        agora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return {"extraido_em_utc": agora, **campos}
