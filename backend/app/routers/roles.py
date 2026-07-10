from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import require_admin
from app.db.session import get_db