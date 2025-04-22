# /services/api_discovery_export/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY dynamic_openapi.py .

RUN pip install fastapi uvicorn clickhouse-connect pyyaml

CMD ["uvicorn", "dynamic_openapi:app", "--host", "0.0.0.0", "--port", "8000"]
