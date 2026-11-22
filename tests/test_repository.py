import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, SessionStatus, TrainingResult
from app.db.repository import DuplicateUpdate, TrainingRepository


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_resume_cancel_idempotency_and_result(db_factory):
    async with db_factory() as db:
        async with db.begin():
            repository = TrainingRepository(db)
            await repository.claim_update(100)
            training = await repository.create_session(
                user_id=42,
                chat_id=42,
                display_name=None,
                material_slug="demo-basic-safety",
                material_version="1.0.0",
            )
            session_id = training.id

    async with db_factory() as db:
        async with db.begin():
            repository = TrainingRepository(db)
            resumed = await repository.active_session(42)
            assert resumed and resumed.id == session_id
            resumed.status = SessionStatus.quiz
            resumed.checked_answers = 3
            resumed.correct_answers = 2
            resumed.started_at = datetime.now(timezone.utc)
            first = await repository.complete(resumed)
            second = await repository.complete(resumed)
            assert first.id == second.id
        assert await db.scalar(select(func.count()).select_from(TrainingResult)) == 1

    async with db_factory() as db:
        async with db.begin():
            repository = TrainingRepository(db)
            with pytest.raises(DuplicateUpdate):
                await repository.claim_update(100)

    async with db_factory() as db:
        async with db.begin():
            repository = TrainingRepository(db)
            await repository.create_session(
                user_id=43,
                chat_id=43,
                display_name=None,
                material_slug="demo-basic-safety",
                material_version="1.0.0",
            )
            assert await repository.cancel_active(43) is True
            assert await repository.active_session(43) is None
