import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.exceptions import BusinessRuleError, NotFoundError
from app.routers import (
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
app.include_router(users_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(definitions_router, prefix="/api/v1")


@app.exception_handler(NotFoundError)
async def not_found_handler(_, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(_, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health_check():
    return {"status": "healthy"}