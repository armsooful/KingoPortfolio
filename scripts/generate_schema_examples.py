#!/usr/bin/env python3
"""
Generate example JSON payloads from actual schemas.

Sources:
- FastAPI OpenAPI schema for endpoints (app.openapi())
- Standalone JSON Schema files (e.g., Output Schema v3)

Usage:
  python scripts/generate_schema_examples.py --out docs/generated_schema_examples.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, Tuple


DEFAULT_ENDPOINTS = [
    "POST /api/diagnosis/submit",
    "POST /portfolio/generate",
    "POST /portfolio/custom",
    "GET /api/v1/portfolios/{portfolio_id}/performance",
    "GET /api/v1/portfolios/{portfolio_id}/metrics/{metric_key}",
    "POST /api/v1/analysis/explain",
    "POST /api/v1/analysis/compare-periods",
    "POST /api/v1/analysis/history",
    "GET /api/v1/analysis/history",
    "POST /api/v1/events",
    "POST /api/v1/analysis/explain/pdf",
    "POST /api/v1/analysis/premium-report/pdf",
]

DEFAULT_JSON_SCHEMAS = [
    "docs/phase8/output_schema_v3.json",
]


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _pick_non_null(schema: Dict[str, Any]) -> Dict[str, Any]:
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            if candidate.get("type") != "null":
                return candidate
    if "oneOf" in schema:
        for candidate in schema["oneOf"]:
            if candidate.get("type") != "null":
                return candidate
    return schema


def _example_from_schema(
    schema: Dict[str, Any],
    components: Dict[str, Any],
    depth: int = 0,
) -> Any:
    if depth > 20:
        return None

    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/components/"):
            return None
        _, _, tail = ref.partition("#/components/")
        target = components
        for part in tail.split("/"):
            target = target.get(part, {})
        return _example_from_schema(target, components, depth + 1)

    schema = _pick_non_null(schema)

    if "example" in schema:
        return schema["example"]
    if "examples" in schema and isinstance(schema["examples"], list) and schema["examples"]:
        return schema["examples"][0]

    if "allOf" in schema:
        merged: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for part in schema["allOf"]:
            resolved = _example_from_schema(part, components, depth + 1)
            if isinstance(resolved, dict):
                # best effort: merge objects
                for k, v in resolved.items():
                    merged["properties"][k] = v
        return _example_from_schema(merged, components, depth + 1)

    if "enum" in schema:
        return schema["enum"][0]

    t = schema.get("type")
    if t == "object" or ("properties" in schema):
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        result: Dict[str, Any] = {}
        # include required first, then the rest
        for key in list(required) + [k for k in props.keys() if k not in required]:
            result[key] = _example_from_schema(props.get(key, {}), components, depth + 1)
        return result
    if t == "array":
        items = schema.get("items", {})
        return [_example_from_schema(items, components, depth + 1)]
    if t == "string":
        fmt = schema.get("format")
        if fmt == "date":
            return "2026-02-06"
        if fmt == "date-time":
            return _now_iso()
        if fmt == "email":
            return "user@example.com"
        return "string"
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False

    return None


def _resolve_response_schema(path_item: Dict[str, Any], method: str) -> Tuple[int, Dict[str, Any], str]:
    op = path_item.get(method.lower())
    if not op:
        return 0, {}, "method_not_found"

    responses = op.get("responses", {})
    # prefer 200/201, then any 2xx
    for code in ("200", "201"):
        if code in responses:
            return int(code), responses[code], "ok"
    for code, resp in responses.items():
        if code.isdigit() and 200 <= int(code) < 300:
            return int(code), resp, "ok"
    return 0, {}, "no_success_response"


def _example_for_endpoint(openapi: Dict[str, Any], method: str, path: str) -> Dict[str, Any]:
    paths = openapi.get("paths", {})
    path_item = paths.get(path)
    if not path_item:
        return {"error": "path_not_found"}

    status, resp, status_note = _resolve_response_schema(path_item, method)
    if status_note != "ok":
        return {"error": status_note}

    content = resp.get("content", {})
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        example = _example_from_schema(schema, openapi.get("components", {}))
        return {"status": status, "example": example, "content_type": "application/json"}
    if "application/pdf" in content:
        return {
            "status": status,
            "content_type": "application/pdf",
            "example_headers": {
                "Content-Type": "application/pdf",
                "Content-Disposition": "attachment; filename=report.pdf",
            },
        }

    return {"status": status, "error": "unsupported_content_type"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate example JSON payloads from schemas.")
    parser.add_argument("--out", default="docs/generated_schema_examples.json")
    parser.add_argument("--endpoint", action="append", default=[])
    parser.add_argument("--schema", action="append", default=[])
    args = parser.parse_args()

    endpoints = args.endpoint or DEFAULT_ENDPOINTS
    schemas = args.schema or DEFAULT_JSON_SCHEMAS

    # Load FastAPI app
    try:
        from backend.app.main import app  # type: ignore
        openapi = app.openapi()
    except Exception as exc:
        openapi = {"_error": f"Failed to load app.openapi(): {exc}"}

    output: Dict[str, Any] = {
        "generated_at": _now_iso(),
        "endpoints": {},
        "schemas": {},
    }

    if "_error" in openapi:
        output["errors"] = {"openapi": openapi["_error"]}
    else:
        for item in endpoints:
            try:
                method, path = item.split(" ", 1)
            except ValueError:
                output["endpoints"][item] = {"error": "invalid_endpoint_format"}
                continue
            output["endpoints"][item] = _example_for_endpoint(openapi, method, path)

    for schema_path in schemas:
        if not os.path.exists(schema_path):
            output["schemas"][schema_path] = {"error": "file_not_found"}
            continue
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        example = _example_from_schema(schema, {"schemas": {}})
        output["schemas"][schema_path] = {"example": example}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote examples to {args.out}")


if __name__ == "__main__":
    main()
