import os

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from .redirect import get_or_create_redirect
from .settings import Settings
from .studies import StudiesFileError, parse_studies_file


class HealthResponse(BaseModel):
    status: str
    errors: list[str]


def build_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]
    app = FastAPI(title="Study Roulette")

    def check_health() -> tuple[bool, list[str]]:
        errors: list[str] = []

        lookup_dir = settings.lookup_dir
        if not lookup_dir.exists():
            try:
                lookup_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(f"Cannot create LOOKUP_DIR: {e}")

        if lookup_dir.exists():
            if not os.access(lookup_dir, os.R_OK):
                errors.append(f"LOOKUP_DIR is not readable: {lookup_dir}")
            if not os.access(lookup_dir, os.W_OK):
                errors.append(f"LOOKUP_DIR is not writable: {lookup_dir}")

            try:
                test_file = lookup_dir / ".health_check"
                test_file.write_text("test")
                test_file.read_text()
                test_file.unlink()
            except OSError as e:
                errors.append(f"Cannot read/write in LOOKUP_DIR: {e}")

        studies_file = settings.studies_file
        if not studies_file.exists():
            errors.append(f"STUDIES_FILE does not exist: {studies_file}")
        elif not os.access(studies_file, os.R_OK):
            errors.append(f"STUDIES_FILE is not readable: {studies_file}")
        else:
            try:
                parse_studies_file(studies_file)
            except StudiesFileError as e:
                errors.append(str(e))

        return (len(errors) == 0, errors)

    def error_response(errors: list[str]) -> JSONResponse:
        response = HealthResponse(status="error", errors=errors)
        return JSONResponse(content=response.model_dump(), status_code=500)

    @app.get("/health")
    def health() -> JSONResponse:
        is_healthy, errors = check_health()

        if not is_healthy:
            return error_response(errors)

        response = HealthResponse(status="ok", errors=[])
        return JSONResponse(content=response.model_dump(), status_code=200)

    @app.get("/sr")
    def redirect(request: Request) -> Response:
        is_healthy, errors = check_health()
        if not is_healthy:
            return error_response(errors)

        params: dict[str, list[str]] = {}
        for key, value in request.query_params.multi_items():
            if key not in params:
                params[key] = []
            params[key].append(value)

        try:
            destination = get_or_create_redirect(
                lookup_dir=settings.lookup_dir,
                studies_file=settings.studies_file,
                params=params,
            )
            return RedirectResponse(url=destination, status_code=302)
        except Exception as e:
            return error_response([str(e)])

    return app
