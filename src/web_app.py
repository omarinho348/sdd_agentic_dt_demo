"""Local browser application for the TwinIt DTDL generator."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent))

from dtdl_generator import (  # noqa: E402
    AssemblyLineParameters,
    DTDLInterface,
    build_dtdl_document,
    extract_parameters,
    missing_fields,
    persist_document,
)


HOST = "127.0.0.1"
PORT = 8000
WEB_ROOT = Path(__file__).parent / "web"
OUTPUT_PATH = Path("assembly_line.json")


class WebValidationError(ValueError):
    """A client-correctable validation error for the browser API."""

    def __init__(self, errors: list[dict[str, Any]]):
        self.errors = errors
        super().__init__("Request contains invalid or incomplete parameters")


def _document_payload(document: list[DTDLInterface]) -> list[dict[str, Any]]:
    return [item.model_dump(by_alias=True, exclude_none=True) for item in document]


def extract_request(payload: dict[str, Any], client: Any = None) -> dict[str, Any]:
    description = payload.get("description")
    if not isinstance(description, str) or not description.strip():
        raise WebValidationError([{"field": "description", "message": "Enter a description."}])
    parameters = extract_parameters(description.strip(), client=client)
    return {
        "parameters": parameters.model_dump(),
        "missing_fields": missing_fields(parameters),
    }


def generate_request(
    payload: dict[str, Any],
    output_path: Path = OUTPUT_PATH,
) -> dict[str, Any]:
    raw_parameters = payload.get("parameters", payload)
    if not isinstance(raw_parameters, dict):
        raise WebValidationError([{"field": "parameters", "message": "Parameters must be an object."}])
    try:
        parameters = AssemblyLineParameters.model_validate(raw_parameters)
    except ValidationError as error:
        raise WebValidationError(
            [
                {
                    "field": str(item["loc"][0]),
                    "message": item["msg"],
                }
                for item in error.errors()
            ]
        ) from error
    unresolved = missing_fields(parameters)
    if unresolved:
        raise WebValidationError(
            [{"field": field, "message": "This value is required."} for field in unresolved]
        )
    document = build_dtdl_document(parameters)
    persist_document(document, output_path=output_path)
    return {
        "parameters": parameters.model_dump(),
        "document": _document_payload(document),
        "download_name": output_path.name,
    }


class TwinItHandler(BaseHTTPRequestHandler):
    server_version = "TwinIt/1.0"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif path in {"/app.js", "/styles.css"}:
            content_type = "application/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
            self._serve_file(path.lstrip("/"), content_type)
        else:
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            path = urlparse(self.path).path
            if path == "/api/extract":
                result = extract_request(payload)
            elif path == "/api/generate":
                result = generate_request(payload)
            else:
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(result, HTTPStatus.OK)
        except WebValidationError as error:
            self._send_json({"errors": error.errors}, HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as error:  # Keep API failures readable in the browser.
            self._send_json({"error": str(error)}, HTTPStatus.BAD_GATEWAY)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {format % args}")

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as error:
            raise WebValidationError([{"field": "request", "message": "Send valid JSON."}]) from error
        if not isinstance(payload, dict):
            raise WebValidationError([{"field": "request", "message": "Send a JSON object."}])
        return payload

    def _serve_file(self, filename: str, content_type: str) -> None:
        file_path = (WEB_ROOT / filename).resolve()
        if WEB_ROOT.resolve() not in file_path.parents:
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            content = file_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict[str, Any] | list[Any], status: HTTPStatus) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def serve(host: str = HOST, port: int = PORT) -> None:
    server = HTTPServer((host, port), TwinItHandler)
    print(f"TwinIt is ready at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nTwinIt stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
