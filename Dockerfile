FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# trusted-host: o build roda atrás de inspeção TLS nesta rede.
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "sigmu_pipeline.cli"]
