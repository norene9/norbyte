class NotFoundError(Exception):
    """Base exception for missing resources."""


class BusinessRuleError(Exception):
    """Raised when a service operation violates a business rule."""


class ConnectionNotFoundError(NotFoundError):
    def __init__(self, connection_id: int):
        super().__init__(f"Connection with id {connection_id} was not found")
        self.connection_id = connection_id


class ProjectNotFoundError(NotFoundError):
    def __init__(self, project_id: int):
        super().__init__(f"Project with id {project_id} was not found")
        self.project_id = project_id


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: int):
        super().__init__(f"User with id {user_id} was not found")
        self.user_id = user_id


class SourceDefinitionNotFoundError(NotFoundError):
    def __init__(self, source_id: int):
        super().__init__(f"Source definition with id {source_id} was not found")
        self.source_id = source_id


class DestinationDefinitionNotFoundError(NotFoundError):
    def __init__(self, destination_id: int):
        super().__init__(f"Destination definition with id {destination_id} was not found")
        self.destination_id = destination_id
