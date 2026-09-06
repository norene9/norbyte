from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import ConnectionRepository, DefinitionRepository, SemanticRepository
from app.services.connection_service import ConnectionService
from app.services.definition_service import DefinitionService
from app.services.sync_service import SyncService
from app.services.semantic_service import SemanticService


def get_connection_service(db: Session = Depends(get_db)) -> ConnectionService:
    return ConnectionService(ConnectionRepository(db))


def get_sync_service(db: Session = Depends(get_db)) -> SyncService:
    return SyncService(db, ConnectionRepository(db), DefinitionService(DefinitionRepository(db)))


def get_semantic_service(db: Session = Depends(get_db)) -> SemanticService:
    return SemanticService(
        SemanticRepository(db),
        ConnectionRepository(db),
        DefinitionService(DefinitionRepository(db)),
    )
