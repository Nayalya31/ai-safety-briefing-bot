import uuid

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.materials import QuizQuestion


def material_keyboard(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть демо", callback_data=f"material:{slug}")]])


def ready_keyboard(session_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Перейти к проверке", callback_data=f"ready:{session_id}")]]
    )


def answer_keyboard(session_id: uuid.UUID, question_index: int, question: QuizQuestion) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=option, callback_data=f"answer:{session_id}:{question_index}:{index}")]
        for index, option in enumerate(question.options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
