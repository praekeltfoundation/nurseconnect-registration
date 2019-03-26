import pytest

from seaworthy.containers.postgresql import PostgreSQLContainer
from seaworthy.definitions import ContainerDefinition

NCREG_IMAGE = pytest.config.getoption("--ncreg-image")


class NCRegContainer(ContainerDefinition):
    WAIT_PATTERNS = (r"Listening at: unix:/run/gunicorn/gunicorn.sock",)

    def __init__(self, name, db_url, image=NCREG_IMAGE):
        super().__init__(name, image, self.WAIT_PATTERNS)
        self.db_url = db_url

    def base_kwargs(self):
        return {
            "ports": {"8000/tcp": None},
            "environment": {"DATABASE_URL": self.db_url},
        }


postgresql_container = PostgreSQLContainer("postgresql")
f = postgresql_container.pytest_clean_fixtures("postgresql_container")
postgresql_fixture, clean_postgresql_fixture = f

ncreg_container = NCRegContainer(
    "nurseconnect_registration", postgresql_container.database_url()
)
ncreg_fixture = ncreg_container.pytest_fixture(
    "ncreg_container", dependencies=["postgresql_container"]
)

__all__ = ["clean_postgresql_fixture", "ncreg_fixture", "postgresql_fixture"]
