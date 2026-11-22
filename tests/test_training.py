from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.db.models import SessionStatus, TrainingSession
from app.services.training import TrainingService


def make_session(status: SessionStatus = SessionStatus.quiz) -> TrainingSession:
    return TrainingSession(
        id=uuid4(),
        telegram_user_id=1,
        telegram_chat_id=1,
        material_slug="demo-basic-safety",
        material_version="1.0.0",
        status=status,
        current_question=0,
        checked_answers=0,
        correct_answers=0,
        started_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_answer_selection_and_score(material):
    session = make_session()
    service = TrainingService()
    first = service.answer(session, material, 0, material.questions[0].correct_option)
    assert first.correct is True
    service.answer(session, material, 1, 0)
    final = service.answer(session, material, 2, material.questions[2].correct_option)
    assert final.completed is True
    assert session.checked_answers == 3
    assert session.correct_answers == 2


def test_duplicate_question_is_rejected(material):
    session = make_session()
    service = TrainingService()
    service.answer(session, material, 0, 0)
    with pytest.raises(ValueError, match="уже обработан"):
        service.answer(session, material, 0, 0)


def test_start_quiz():
    session = make_session(SessionStatus.learning)
    TrainingService.start_quiz(session)
    assert session.status == SessionStatus.quiz
