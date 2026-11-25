"""One JSON shape for every error: {"error": {"code": "...", "message": "..."}}."""
import logging
from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException

logger = logging.getLogger("uvicorn.error")

CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
         405: "method_not_allowed", 503: "unavailable"}


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def bad_request(message: str) -> ApiError:
    return ApiError(400, message)


def unauthorized(message: str) -> ApiError:
    return ApiError(401, message)


def not_found(kind: str, value: object) -> ApiError:
    return ApiError(404, f"Unknown {kind}: {value}")


def _response(status: int, message: str,
              headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    code = CODES.get(status, "error")
    if status == 401:
        headers = {"WWW-Authenticate": "Bearer"}
    return JSONResponse({"error": {"code": code, "message": message}}, status, headers)


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    def api_error(request: Request, error: ApiError) -> JSONResponse:
        return _response(error.status, error.message)

    @app.exception_handler(RequestValidationError)
    def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        # Only where and what: the rejected value could be a password.
        details = [f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                   for item in error.errors()]
        return _response(400, "; ".join(details))

    @app.exception_handler(HTTPException)
    def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return _response(error.status_code, str(error.detail), error.headers)

    @app.exception_handler(OperationalError)
    def database_error(request: Request, error: OperationalError) -> JSONResponse:
        logger.error("Database error: %s", error.orig)
        return _response(503, "The database is not available")

    @app.exception_handler(Exception)
    def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        return _response(500, "Internal error")
