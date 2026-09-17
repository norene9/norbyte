import re
from datetime import datetime, timezone

from fastapi import HTTPException
from app.connectors.registry import get_destination_connector
from app.core.encryption import decrypt_config
from app.exceptions import ProjectNotFoundError
from app.models import Connection, Project, SavedCube
from app.repositories.saved_cube_repository import SavedCubeRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.definition_repository import DefinitionRepository
from app.schemas.saved_cube import SavedCubeCreate, SavedCubeUpdate
from app.schemas.query import QueryRequest
from app.services.query_engine import QueryEngine


class SavedCubeService:
    def __init__(self, repository: SavedCubeRepository, query_engine: QueryEngine):
        self.repository = repository
        self.query_engine = query_engine

    def _project(self, project_id: int, user_id: int) -> Project:
        project = ProjectRepository(self.repository.db).get_by_id(project_id, user_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    def _validate_table_name(self, table_name: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
            raise HTTPException(status_code=422, detail="output_table must be a valid SQL identifier")
        return table_name

    def _data(self, dto: SavedCubeCreate | SavedCubeUpdate, existing: SavedCube | None = None) -> dict:
        data = dto.model_dump(exclude_unset=True)
        if "query_definition" in data:
            data["query_definition"] = dto.query_definition.model_dump()
        if "output_table" in data and data["output_table"]:
            data["output_table"] = self._validate_table_name(data["output_table"])
        if existing is None and not data.get("output_table"):
            data["output_table"] = self._validate_table_name(f"cube_{re.sub(r'[^A-Za-z0-9_]', '_', data['name']).strip('_').lower()}")
        return data

    def create(self, project_id: int, user_id: int, dto: SavedCubeCreate) -> SavedCube:
        self._project(project_id, user_id)
        return self.repository.create(project_id, self._data(dto))

    def get(self, project_id: int, user_id: int, cube_id: int) -> SavedCube:
        self._project(project_id, user_id)
        cube = self.repository.get(cube_id, project_id)
        if not cube:
            raise HTTPException(status_code=404, detail="Saved cube not found")
        return cube

    def list(self, project_id: int, user_id: int) -> list[SavedCube]:
        self._project(project_id, user_id)
        return self.repository.list(project_id)

    def update(self, project_id: int, user_id: int, cube_id: int, dto: SavedCubeUpdate) -> SavedCube:
        cube = self.get(project_id, user_id, cube_id)
        if dto.output_table:
            self._validate_table_name(dto.output_table)
        if dto.query_definition is not None or dto.output_table is not None:
            self._drop_output_table(cube)
            cube.last_refreshed_at = None
        return self.repository.update(cube, dto)

    def delete(self, project_id: int, user_id: int, cube_id: int) -> None:
        cube = self.get(project_id, user_id, cube_id)
        self._drop_output_table(cube)
        self.repository.delete(cube)

    def refresh(self, project_id: int, user_id: int, cube_id: int) -> SavedCube:
        cube = self.get(project_id, user_id, cube_id)
        sql, params = self.query_engine.build(project_id, QueryRequest(**cube.query_definition))
        connection = (
            self.repository.db.query(Connection)
            .filter(Connection.project_id == project_id)
            .order_by(Connection.id.asc())
            .first()
        )
        if not connection:
            raise HTTPException(status_code=404, detail="No connection found for project")
        destination = DefinitionRepository(self.repository.db).get_destination_by_id(connection.destination_id)
        if not destination:
            raise HTTPException(status_code=404, detail="Destination definition not found")
        connector = get_destination_connector(destination.connector_type)(decrypt_config(connection.destination_connection_json))
        schema = connector.config.get("schema", "public")
        conn = connector._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f'DROP TABLE IF EXISTS "{schema}"."{cube.output_table}"'
                )
                cursor.execute(
                    f'CREATE TABLE "{schema}"."{cube.output_table}" AS {sql}',
                    params,
                )
            conn.commit()
        finally:
            conn.close()
        cube.last_refreshed_at = datetime.now(timezone.utc).isoformat()
        self.repository.db.add(cube)
        self.repository.db.commit()
        self.repository.db.refresh(cube)
        return cube

    def _drop_output_table(self, cube: SavedCube) -> None:
        connection = (
            self.repository.db.query(Connection)
            .filter(Connection.project_id == cube.project_id)
            .order_by(Connection.id.asc())
            .first()
        )
        if not connection:
            return
        destination = DefinitionRepository(self.repository.db).get_destination_by_id(connection.destination_id)
        if not destination:
            return
        connector = get_destination_connector(destination.connector_type)(decrypt_config(connection.destination_connection_json))
        schema = connector.config.get("schema", "public")
        conn = connector._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f'DROP TABLE IF EXISTS "{schema}"."{cube.output_table}"')
            conn.commit()
        finally:
            conn.close()