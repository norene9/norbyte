import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.security import get_current_user
from app.db.session import initialize_database
from app.exceptions import BusinessRuleError, NotFoundError
from app.routers import (
    auth_router,
    users_router,
    projects_router,
    connections_router,
    definitions_router,
)

# Initialize FastAPI Application
app = FastAPI(
    title="Norbyte Data Integration Engine",
    description="Automated zero-maintenance API & Database replication platform.",
    version="1.0.0"
)

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
app.mount("/destinations", StaticFiles(directory="destinations"), name="destinations")

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


@app.on_event("startup")
def create_tables():
    initialize_database()


@app.exception_handler(NotFoundError)
async def not_found_handler(_, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(_, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "healthy"}