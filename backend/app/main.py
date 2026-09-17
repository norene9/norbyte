import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.security import get_current_user
from app.exceptions import BusinessRuleError, NotFoundError
from app.routers import (
    auth_router,
    users_router,
    projects_router,
    connections_router,
    definitions_router,
    semantic_router,
    saved_cubes_router,
)

# Initialize FastAPI Application
app = FastAPI(
    title="Norbyte Data Integration Engine",
    description="Automated zero-maintenance API & Database replication platform.",
    version="1.0.0"
)


def _downgrade_file_schemas_for_swagger_ui(node):
    """Swagger UI doesn't render file-upload widgets for OpenAPI 3.1's
    `contentMediaType` keyword on array items, only for the older 3.0
    `format: binary` style. Rewrite the schema recursively so file inputs
    (including multi-file arrays) show up correctly in /docs."""
    if isinstance(node, dict):
        if node.get("contentMediaType"):
            node.pop("contentMediaType", None)
            node.pop("contentEncoding", None)
            node["type"] = "string"
            node["format"] = "binary"
        for value in node.values():
            _downgrade_file_schemas_for_swagger_ui(value)
    elif isinstance(node, list):
        for item in node:
            _downgrade_file_schemas_for_swagger_ui(item)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["openapi"] = "3.0.3"
    _downgrade_file_schemas_for_swagger_ui(schema)
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(definitions_router, prefix="/api/v1")
app.include_router(semantic_router, prefix="/api/v1")
app.include_router(saved_cubes_router, prefix="/api/v1")
app.mount("/destinations", StaticFiles(directory="/data/uploads/destinations"), name="destinations")
app.mount("/sources", StaticFiles(directory="/data/uploads/sources"), name="sources")

@app.middleware("http")
async def enforce_authentication(request: Request, call_next):
    public_paths = {
        "/health",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
    }
    if request.url.path in public_paths or request.url.path.rstrip("/") == "/api/v1/users":
        return await call_next(request)

    if request.method == "POST" and request.url.path.rstrip("/") == "/api/v1/users":
        return await call_next(request)

    if request.url.path.startswith("/api/v1/"):
        try:
            get_current_user(request)
        except Exception as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc.detail if hasattr(exc, "detail") else exc)})

    return await call_next(request)


@app.exception_handler(NotFoundError)
async def not_found_handler(_, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(_, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "healthy"}