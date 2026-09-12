from fastapi import HTTPException

from app.models import SemanticField, SemanticRelationship, SemanticTable
from app.repositories.semantic_repository import SemanticRepository
from app.schemas.query import QueryRequest


ALLOWED_AGGREGATIONS = {"sum", "avg", "count", "min", "max"}
ALLOWED_OPERATORS = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "contains": "ILIKE",
    "in": "IN",
}


class QueryEngine:
    def __init__(self, semantic_repo: SemanticRepository):
        self.semantic_repo = semantic_repo

    def _resolve_table(self, project_id: int, table_name: str) -> SemanticTable:
        table = (
            self.semantic_repo.db.query(SemanticTable)
            .filter(SemanticTable.project_id == project_id, SemanticTable.display_name == table_name)
            .first()
        )
        if not table:
            table = (
                self.semantic_repo.db.query(SemanticTable)
                .filter(SemanticTable.project_id == project_id, SemanticTable.physical_table == table_name)
                .first()
            )
        if not table:
            raise HTTPException(status_code=422, detail=f"Unknown table '{table_name}'")
        return table

    def _resolve_field(
        self,
        table: SemanticTable,
        field_name: str,
        expected_type: str | None = None,
        joined_tables: list[SemanticTable] | None = None,
    ) -> SemanticField:
        candidate_tables = [table]
        if joined_tables:
            candidate_tables.extend(joined_tables)

        for candidate in candidate_tables:
            field = next(
                (
                    f
                    for f in candidate.fields
                    if f.column_name == field_name or f.display_name == field_name
                ),
                None,
            )
            if field:
                if expected_type and field.field_type != expected_type:
                    raise HTTPException(status_code=422, detail=f"'{field_name}' is not a {expected_type}")
                return field

        raise HTTPException(status_code=422, detail=f"Unknown field '{field_name}' on table '{table.display_name}'")

    def _field_expr(self, alias: str, field: SemanticField) -> str:
        return f'{alias}."{field.column_name}"'

    def _join_expr(self, alias: str, column: str, json_path: str | None) -> str:
        expr = f'{alias}."{column}"'
        if json_path:
            expr = f"{expr} ->> '{json_path}'"
        return expr

    def build(self, project_id: int, request: QueryRequest) -> tuple[str, list]:
        base_table = self._resolve_table(project_id, request.table)
        base_alias = "t0"
        select_parts: list[str] = []
        group_by_parts: list[str] = []
        join_clauses: list[str] = []
        params: list = []
        alias_map: dict[int, str] = {base_table.id: base_alias}
        joined_tables: list[SemanticTable] = []

        for join_name in request.joins:
            relationship = (
                self.semantic_repo.db.query(SemanticRelationship)
                .filter(
                    SemanticRelationship.project_id == project_id,
                    SemanticRelationship.name == join_name,
                )
                .first()
            )
            if not relationship:
                raise HTTPException(status_code=422, detail=f"Unknown relationship '{join_name}'")

            to_table = self.semantic_repo.get_table_by_id(relationship.to_table_id)
            if not to_table:
                raise HTTPException(status_code=422, detail=f"Unknown related table for relationship '{join_name}'")

            joined_tables.append(to_table)
            to_alias = f"t{len(alias_map)}"
            alias_map[to_table.id] = to_alias
            from_alias = alias_map.get(relationship.from_table_id, base_alias)

            left = self._join_expr(from_alias, relationship.from_column, relationship.from_json_path)
            right = self._join_expr(to_alias, relationship.to_column, relationship.to_json_path)
            join_clauses.append(
                f'JOIN "{to_table.physical_table}" {to_alias} ON {left} = {right}'
            )

        for dimension_name in request.dimensions:
            field = self._resolve_field(base_table, dimension_name, expected_type="dimension", joined_tables=joined_tables)
            expr = self._field_expr(base_alias, field)
            if field.semantic_table_id != base_table.id:
                table_alias = alias_map.get(field.semantic_table_id, base_alias)
                expr = self._field_expr(table_alias, field)
            select_parts.append(f'{expr} AS "{field.column_name}"')
            group_by_parts.append(expr)

        for measure in request.measures:
            field = self._resolve_field(base_table, measure.field, expected_type="measure", joined_tables=joined_tables)
            aggregation = (measure.aggregation or field.default_aggregation or "sum").lower()
            if aggregation not in ALLOWED_AGGREGATIONS:
                raise HTTPException(status_code=422, detail=f"Invalid aggregation '{aggregation}'")
            expr = self._field_expr(base_alias, field)
            if field.semantic_table_id != base_table.id:
                table_alias = alias_map.get(field.semantic_table_id, base_alias)
                expr = self._field_expr(table_alias, field)
            select_parts.append(f'{aggregation.upper()}({expr}) AS "{field.column_name}_{aggregation}"')

        if not select_parts:
            raise HTTPException(status_code=422, detail="Query must include at least one dimension or measure")

        where_parts: list[str] = []
        for item in request.filters:
            field = self._resolve_field(base_table, item.field, joined_tables=joined_tables)
            expr = self._field_expr(base_alias, field)
            if field.semantic_table_id != base_table.id:
                table_alias = alias_map.get(field.semantic_table_id, base_alias)
                expr = self._field_expr(table_alias, field)
            operator = ALLOWED_OPERATORS.get(item.operator)
            if not operator:
                raise HTTPException(status_code=422, detail=f"Invalid operator '{item.operator}'")

            if item.operator == "contains":
                where_parts.append(f"{expr} {operator} %s")
                params.append(f"%{item.value}%")
            elif item.operator == "in":
                if not isinstance(item.value, list):
                    raise HTTPException(status_code=422, detail="'in' filters require a list value")
                placeholders = ", ".join(["%s"] * len(item.value))
                where_parts.append(f"{expr} IN ({placeholders})")
                params.extend(item.value)
            else:
                where_parts.append(f"{expr} {operator} %s")
                params.append(item.value)

        sql = f'SELECT {", ".join(select_parts)} FROM "{base_table.physical_table}" {base_alias}'
        if join_clauses:
            sql += " " + " ".join(join_clauses)
        if where_parts:
            sql += f" WHERE {' AND '.join(where_parts)}"
        if group_by_parts:
            sql += f" GROUP BY {', '.join(group_by_parts)}"
        sql += f" LIMIT {int(request.limit)}"

        return sql, params
