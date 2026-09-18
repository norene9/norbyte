import os
import sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base_class import Base
from app.exceptions import BusinessRuleError, ProjectNotFoundError, UserNotFoundError
from app.models import Project, User
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.user import UserCreate
from app.services.project_service import ProjectService
from app.services.user_service import UserService


class ResourceServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_project_service_crud_flow(self):
        user = User(username="alice", email="alice@example.com", password="secret")
        self.session.add(user)
        self.session.commit()

        service = ProjectService(ProjectRepository(self.session))
        created = service.create(ProjectCreate(name="Demo", description="Test"), user_id=user.id)
        self.assertEqual(created.name, "Demo")

        fetched = service.get(created.id, user_id=user.id)
        self.assertEqual(fetched.id, created.id)

        updated = service.update(created.id, ProjectUpdate(name="Updated"), user_id=user.id)
        self.assertEqual(updated.name, "Updated")

        service.delete(created.id, user_id=user.id)
        with self.assertRaises(ProjectNotFoundError):
            service.get(created.id, user_id=user.id)

    def test_project_service_restricts_access_to_owner(self):
        user_a = User(username="alice", email="alice@example.com", password="secret")
        user_b = User(username="bob", email="bob@example.com", password="secret")
        self.session.add_all([user_a, user_b])
        self.session.commit()

        service = ProjectService(ProjectRepository(self.session))
        project = service.create(ProjectCreate(name="Owned project"), user_id=user_a.id)

        self.assertEqual(project.user_id, user_a.id)
        self.assertEqual(len(service.list(user_id=user_a.id)), 1)
        self.assertEqual(len(service.list(user_id=user_b.id)), 0)

        with self.assertRaises(ProjectNotFoundError):
            service.get(project.id, user_id=user_b.id)

    def test_user_service_enforces_unique_username(self):
        service = UserService(UserRepository(self.session))
        service.create(UserCreate(username="alice", email="alice@example.com", password="secret"))

        with self.assertRaises(BusinessRuleError):
            service.create(UserCreate(username="alice", email="bob@example.com", password="secret"))

        with self.assertRaises(UserNotFoundError):
            service.get(999)


if __name__ == "__main__":
    unittest.main()
