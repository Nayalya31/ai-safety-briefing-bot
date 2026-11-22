import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProcessedUpdate, SessionStatus, TrainingResult, TrainingSession


class DuplicateUpdate(Exception):
    pass


class TrainingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim_update(self, update_id: int) -> None:
        try:
            async with self.session.begin_nested():
                self.session.add(ProcessedUpdate(update_id=update_id))
                await self.session.flush()
        except IntegrityError as exc:
            raise DuplicateUpdate from exc

    async def active_session(self, user_id: int) -> TrainingSession | None:
        statement = (
            select(TrainingSession)
            .where(
                TrainingSession.telegram_user_id == user_id,
                TrainingSession.status.in_([SessionStatus.learning, SessionStatus.quiz]),
            )
            .order_by(TrainingSession.started_at.desc())
            .limit(1)
        )
        return await self.session.scalar(statement)

    async def get_session(self, session_id: uuid.UUID, user_id: int, *, lock: bool = False) -> TrainingSession | None:
        statement = select(TrainingSession).where(
            TrainingSession.id == session_id,
            TrainingSession.telegram_user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def create_session(
        self,
        *,
        user_id: int,
        chat_id: int,
        display_name: str | None,
        material_slug: str,
        material_version: str,
    ) -> TrainingSession:
        session = TrainingSession(
            telegram_user_id=user_id,
            telegram_chat_id=chat_id,
            display_name=display_name,
            material_slug=material_slug,
            material_version=material_version,
            status=SessionStatus.learning,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def cancel_active(self, user_id: int) -> bool:
        active = await self.active_session(user_id)
        if not active:
            return False
        active.status = SessionStatus.cancelled
        return True

    async def complete(self, training: TrainingSession) -> TrainingResult:
        training.status = SessionStatus.completed
        training.completed_at = datetime.now(timezone.utc)
        existing = await self.session.scalar(select(TrainingResult).where(TrainingResult.session_id == training.id))
        if existing:
            return existing
        score = round(training.correct_answers * 100 / training.checked_answers) if training.checked_answers else 0
        result = TrainingResult(
            session_id=training.id,
            telegram_user_id=training.telegram_user_id,
            material_slug=training.material_slug,
            material_version=training.material_version,
            checked_answers=training.checked_answers,
            correct_answers=training.correct_answers,
            score_percent=score,
            started_at=training.started_at,
            completed_at=training.completed_at,
        )
        self.session.add(result)
        await self.session.flush()
        return result
