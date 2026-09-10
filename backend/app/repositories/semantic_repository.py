from sqlalchemy.orm import Session

from app.models import SemanticRelationship, SemanticTable


class SemanticRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_table(self, semantic_table: SemanticTable) -> SemanticTable:
        self.db.add(semantic_table)
        self.db.commit()
        self.db.refresh(semantic_table)
        return semantic_table

    def get_table_by_id(self, table_id: int) -> SemanticTable | None:
        return self.db.query(SemanticTable).filter(SemanticTable.id == table_id).first()

    def list_tables_by_project(self, project_id: int) -> list[SemanticTable]:
        return self.db.query(SemanticTable).filter(SemanticTable.project_id == project_id).all()

    def update_table(self, semantic_table: SemanticTable) -> SemanticTable:
        self.db.add(semantic_table)
        self.db.commit()
        self.db.refresh(semantic_table)
        return semantic_table

    def delete_table(self, semantic_table: SemanticTable) -> None:
        self.db.delete(semantic_table)
        self.db.commit()

    def create_relationship(self, relationship: SemanticRelationship) -> SemanticRelationship:
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def get_relationship_by_id(self, relationship_id: int) -> SemanticRelationship | None:
        return self.db.query(SemanticRelationship).filter(SemanticRelationship.id == relationship_id).first()

    def list_relationships_by_project(self, project_id: int) -> list[SemanticRelationship]:
        return (
            self.db.query(SemanticRelationship)
            .filter(SemanticRelationship.project_id == project_id)
            .all()
        )

    def update_relationship(self, relationship: SemanticRelationship) -> SemanticRelationship:
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def delete_relationship(self, relationship: SemanticRelationship) -> None:
        self.db.delete(relationship)
        self.db.commit()