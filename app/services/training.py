from dataclasses import dataclass

from app.db.models import SessionStatus, TrainingSession
from app.materials import QuizQuestion, TrainingMaterial


@dataclass(frozen=True)
class AnswerOutcome:
    correct: bool
    completed: bool
    question: QuizQuestion
    selected_option: str


class TrainingService:
    @staticmethod
    def start_quiz(session: TrainingSession) -> None:
        if session.status != SessionStatus.learning:
            raise ValueError("Тест уже начат или сессия завершена")
        session.status = SessionStatus.quiz
        session.current_question = 0

    @staticmethod
    def answer(session: TrainingSession, material: TrainingMaterial, question_index: int, option_index: int) -> AnswerOutcome:
        if session.status != SessionStatus.quiz:
            raise ValueError("Сессия не находится на этапе теста")
        if question_index != session.current_question:
            raise ValueError("Этот вопрос уже обработан")
        if question_index < 0 or question_index >= len(material.questions):
            raise ValueError("Некорректный номер вопроса")
        question = material.questions[question_index]
        if option_index < 0 or option_index >= len(question.options):
            raise ValueError("Некорректный вариант ответа")
        correct = option_index == question.correct_option
        session.checked_answers += 1
        session.correct_answers += int(correct)
        session.current_question += 1
        return AnswerOutcome(
            correct=correct,
            completed=session.current_question >= len(material.questions),
            question=question,
            selected_option=question.options[option_index],
        )
