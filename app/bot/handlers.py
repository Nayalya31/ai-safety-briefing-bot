import uuid

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import answer_keyboard, material_keyboard, ready_keyboard
from app.db import TrainingRepository
from app.db.models import SessionStatus
from app.materials import MaterialCatalog
from app.services import AIExplainer, ModelUnavailable, TrainingService

router = Router()

DISCLAIMER = (
    "Это учебное демо для знакомства с материалом и самопроверки. Оно не заменяет официальный инструктаж, "
    "допуск к работе и процедуры работодателя. При реальном происшествии действуйте по утверждённым процедурам "
    "и обращайтесь к ответственному специалисту."
)


def _user_id(event: Message | CallbackQuery) -> int:
    if not event.from_user:
        raise ValueError("Не удалось определить пользователя Telegram")
    return event.from_user.id


async def _send_question(message: Message, session, catalog: MaterialCatalog) -> None:
    material = catalog.get(session.material_slug)
    question = material.questions[session.current_question]
    await message.answer(
        f"Вопрос {session.current_question + 1} из {len(material.questions)}\n\n{question.text}",
        reply_markup=answer_keyboard(session.id, session.current_question, question),
    )


@router.message(Command("start"))
async def start(message: Message, repository: TrainingRepository, catalog: MaterialCatalog) -> None:
    active = await repository.active_session(_user_id(message))
    if active:
        material = catalog.get(active.material_slug)
        if active.status == SessionStatus.quiz:
            await message.answer("У вас есть незавершённая проверка. Продолжаем с сохранённого места.")
            await _send_question(message, active, catalog)
        else:
            await message.answer(
                f"У вас есть незавершённый инструктаж «{material.title}» версии {material.version}.\n\n{DISCLAIMER}",
                reply_markup=ready_keyboard(active.id),
            )
        return
    demo = next(iter(catalog.materials.values()))
    await message.answer(
        "Здравствуйте! Я помогу изучить короткий демонстрационный материал и проверить понимание.\n\n"
        + DISCLAIMER,
        reply_markup=material_keyboard(demo.slug),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Команды:\n/start — открыть или продолжить инструктаж\n/cancel — отменить текущую сессию\n/help — помощь\n\n"
        "Вопросы задаются по одному. Прогресс сохраняется в базе данных."
    )


@router.message(Command("cancel"))
async def cancel(message: Message, repository: TrainingRepository) -> None:
    cancelled = await repository.cancel_active(_user_id(message))
    await message.answer("Сессия отменена. Отправьте /start, чтобы начать снова." if cancelled else "Активной сессии нет.")


@router.callback_query(F.data.startswith("material:"))
async def open_material(callback: CallbackQuery, repository: TrainingRepository, catalog: MaterialCatalog) -> None:
    assert callback.data and callback.message
    slug = callback.data.split(":", 1)[1]
    material = catalog.get(slug)
    active = await repository.active_session(_user_id(callback))
    if active:
        await callback.answer("Сессия уже открыта")
        return
    session = await repository.create_session(
        user_id=_user_id(callback),
        chat_id=callback.message.chat.id,
        display_name=None,
        material_slug=material.slug,
        material_version=material.version,
    )
    sections = "\n\n".join(f"{section.title}\n{section.text}" for section in material.sections)
    await callback.message.answer(
        f"ДЕМО · {material.title}\nВерсия {material.version}\n\n{material.summary}\n\n{sections}",
        reply_markup=ready_keyboard(session.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ready:"))
async def begin_quiz(
    callback: CallbackQuery,
    repository: TrainingRepository,
    catalog: MaterialCatalog,
    training_service: TrainingService,
) -> None:
    assert callback.data and callback.message
    session_id = uuid.UUID(callback.data.split(":", 1)[1])
    session = await repository.get_session(session_id, _user_id(callback), lock=True)
    if not session:
        await callback.answer("Сессия не найдена", show_alert=True)
        return
    try:
        training_service.start_quiz(session)
    except ValueError:
        await callback.answer("Проверка уже начата")
        return
    await callback.answer()
    await _send_question(callback.message, session, catalog)


@router.callback_query(F.data.startswith("answer:"))
async def answer(
    callback: CallbackQuery,
    repository: TrainingRepository,
    catalog: MaterialCatalog,
    training_service: TrainingService,
    ai_explainer: AIExplainer,
) -> None:
    assert callback.data and callback.message
    _, raw_session_id, raw_question, raw_option = callback.data.split(":")
    session = await repository.get_session(uuid.UUID(raw_session_id), _user_id(callback), lock=True)
    if not session:
        await callback.answer("Сессия не найдена", show_alert=True)
        return
    material = catalog.get(session.material_slug)
    try:
        outcome = training_service.answer(session, material, int(raw_question), int(raw_option))
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    base_feedback = "Верно." if outcome.correct else f"Неверно. Правильный ответ: {outcome.question.options[outcome.question.correct_option]}."
    try:
        explanation = await ai_explainer.explain(
            material=material,
            user_input=(
                f"Вопрос: {outcome.question.text}\nОтвет сотрудника: {outcome.selected_option}\n"
                f"Эталонное пояснение: {outcome.question.explanation}"
            ),
            task="Кратко объясни результат ответа, не меняя факт правильности.",
        )
        detail = f"{explanation.explanation}\nРаздел: {explanation.source_section}"
    except ModelUnavailable:
        detail = f"{outcome.question.explanation}\nРаздел: {material.section_title(outcome.question.section_id)}"

    await callback.answer("Ответ принят")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"{base_feedback}\n{detail}")
    if outcome.completed:
        result = await repository.complete(session)
        await callback.message.answer(
            f"Проверка завершена.\nПравильных ответов: {result.correct_answers} из {result.checked_answers}.\n"
            f"Результат: {result.score_percent}%.\n\nРезультат сохранён. {DISCLAIMER}"
        )
    else:
        await _send_question(callback.message, session, catalog)


@router.message(F.text)
async def explain_text(
    message: Message,
    repository: TrainingRepository,
    catalog: MaterialCatalog,
    ai_explainer: AIExplainer,
) -> None:
    active = await repository.active_session(_user_id(message))
    if not active:
        await message.answer("Отправьте /start, чтобы открыть учебный материал.")
        return
    if active.status == SessionStatus.quiz:
        await message.answer("Во время проверки выберите один из вариантов под текущим вопросом или отправьте /cancel.")
        return
    material = catalog.get(active.material_slug)
    try:
        explanation = await ai_explainer.explain(material=material, user_input=message.text or "", task="Ответь на вопрос по материалу.")
        suffix = "\nСведений в материале недостаточно; обратитесь к ответственному специалисту." if explanation.insufficient_material else ""
        await message.answer(
            f"{explanation.explanation}\nРаздел: {explanation.source_section}{suffix}",
            reply_markup=ready_keyboard(active.id),
        )
    except ModelUnavailable:
        await message.answer(
            "Сейчас не удалось получить объяснение модели. Учебный материал остаётся доступен; можно перейти к проверке.",
            reply_markup=ready_keyboard(active.id),
        )
