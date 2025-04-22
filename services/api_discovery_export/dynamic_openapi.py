from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from clickhouse_connect import get_client
from typing import Dict
import re, yaml

app = FastAPI(
    title="Dynamic API Discovery Spec",
    version="1.0.0",
    description="OpenAPI spec auto-generated from ClickHouse logs"
)

client = get_client(host="clickhouse", port=8123)

EXPORT_PATH = "/tmp/openapi_discovered.yaml"

def normalize_path(path: str) -> str:
    path = re.sub(r"/\\d+", "/{id}", path)
    path = re.sub(r"/[a-f0-9\\-]{8,}", "/{id}", path)
    return path

def build_openapi_spec() -> Dict:
    query = """
        SELECT 
            path, 
            lower(method) AS method, 
            any(authenticated) AS authenticated
        FROM discovered_apis
        GROUP BY path, method
    """
    rows = client.query(query).named_results()

    paths = {}
    for row in rows:
        path = normalize_path(row["path"])
        method = row["method"]
        auth = row["authenticated"]

        operation = {
            "summary": f"Observed {method.upper()} request",
            "description": f"Discovered from traffic logs. Auth required: {auth}",
            "tags": ["Discovered"],
            "x-rate-limit": {"limit": 1000, "interval": "minute"},
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                            "example": {"status": "ok"}
                        }
                    }
                }
            }
        }

        if method in ['post', 'put']:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "example": {"key": "value"}
                        }
                    }
                }
            }

        if "{id}" in path:
            operation["parameters"] = [{
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            }]

        paths.setdefault(path, {})[method] = operation

    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Discovered API Endpoints",
            "version": "1.0.0"
        },
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        },
        "security": [{"bearerAuth": []}]
    }

@app.get("/openapi_dynamic", tags=["dynamic"])
def get_openapi_spec():
    return JSONResponse(content=build_openapi_spec())

@app.get("/openapi_export", tags=["export"])
def export_openapi_to_yaml():
    spec = build_openapi_spec()
    with open(EXPORT_PATH, "w") as f:
        yaml.dump(spec, f, sort_keys=False)
    return FileResponse(EXPORT_PATH, media_type="text/yaml", filename="openapi_discovered.yaml")
