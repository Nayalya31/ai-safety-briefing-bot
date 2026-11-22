from pathlib import Path

import pytest

from app.materials import MaterialCatalog


@pytest.fixture
def material():
    return MaterialCatalog.load(Path("materials")).get("demo-basic-safety")
