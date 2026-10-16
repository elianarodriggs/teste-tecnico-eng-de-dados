FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# nesta rede o certificado do PyPI nao fecha. trusted-host libera so o download do pacote
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt

COPY src ./src
COPY sql ./sql
COPY scripts ./scripts
COPY tests ./tests
COPY pytest.ini .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "src/run_pipeline.py"]
