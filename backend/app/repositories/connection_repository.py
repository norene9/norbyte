from sqlalchemy.orm import Session
from app.models import Connection
from app.schemas.connection import ConnectionCreate, ConnectionUpdate


class ConnectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dto: ConnectionCreate) -> Connection:
        connection = Connection(**dto.model_dump())
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_by_id(self, connection_id: int):
        return self.db.query(Connection).filter(Connection.id == connection_id).first()

    def list(self) -> list[Connection]:
        return self.db.query(Connection).all()

    def update(self, connection: Connection, dto: ConnectionUpdate) -> Connection:
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(connection, key, value)

        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def delete(self, connection: Connection) -> None:
        self.db.delete(connection)
        self.db.commit()
