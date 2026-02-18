import re

from aiogram import Bot, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from redis import Redis

from app.forms import AddLesson, DeleteLesson
from app.models import Lesson
from app.schedule import Schedule

router = Router()


@router.message(CommandStart())
async def on_start(msg: Message) -> None:
    await msg.answer(
        "👋 Привет! Я бот для управления расписанием занятий.\n\n"
        "<b>Доступные команды:</b>\n"
        "/add — добавить урок\n"
        "/list — показать расписание\n"
        "/delete — удалить урок\n"
        "/cancel — отменить урок на один раз\n"
        "/update — изменить урок"
    )


@router.message(Command("add"))
async def on_add(msg: Message, schedule: Schedule) -> None:
    if msg.text is None:
        await msg.reply("Текст сообщения пуст")
        return

    try:
        text = msg.text.split(maxsplit=1)[1]
        lesson = Lesson.from_str(text)
        data = AddLesson(lesson=lesson)
        await schedule.add(data)

        await msg.reply(
            f"✅ Урок добавлен!\n\n"
            f"<b>{lesson.subject}</b>\n"
            f"День: {DAYS_RU[lesson.day]}\n"
            f"Время: {lesson.start_time.strftime('%H:%M')}\n"
            f"Группа: {lesson.group_n}"
        )
    except (ValueError, IndexError):
        await msg.reply(
            "❌ Неверный формат команды.\n\n"
            "<b>Формат:</b> <code>/add [группа] [день] [время] [предмет]</code>\n\n"
            "<b>Пример:</b> <code>/add 1 Пн 10:00 Математика</code>"
        )


@router.message(Command("list"))
async def on_list(msg: Message, schedule: Schedule) -> None:
    lessons = await schedule.get_all_lessons()

    if not lessons:
        await msg.reply("📭 Расписание пусто")
        return

    by_group: dict[str, list[tuple[int, Lesson]]] = {}
    for lesson_id, lesson in lessons:
        by_group.setdefault(lesson.group_n, []).append((lesson_id, lesson))

    text = "📅 <b>Расписание занятий</b>\n\n"

    for group_n in sorted(by_group.keys()):
        text += f"<b>Группа {group_n}:</b>\n"
        for lesson_id, lesson in sorted(
            by_group[group_n], key=lambda x: (x[1].day, x[1].start_time)
        ):
            text += (
                f"#{lesson_id} — {DAYS_RU[lesson.day]} "
                f"{lesson.start_time.strftime('%H:%M')} — "
                f"<i>{lesson.subject}</i>\n"
            )
        text += "\n"

    await msg.reply(text)


@router.message(Command("delete"))
async def on_delete(msg: Message, schedule: Schedule) -> None:
    if msg.text is None:
        await msg.reply("Текст сообщения пуст")
        return

    try:
        lesson_id = int(msg.text.split()[1])
        deleted = await schedule.delete(DeleteLesson(lesson_id=lesson_id))

        if deleted:
            await msg.reply(f"✅ Урок #{lesson_id} удалён")
        else:
            await msg.reply(f"❌ Урок #{lesson_id} не найден")
    except (ValueError, IndexError):
        await msg.reply(
            "❌ Неверный формат команды.\n\n"
            "<b>Формат:</b> <code>/delete [ID урока]</code>\n\n"
            "<b>Пример:</b> <code>/delete 5</code>\n\n"
            "Посмотреть ID можно командой /list"
        )


@router.message(Command("cancel"))
async def on_cancel(msg: Message, redis: Redis) -> None:
    if msg.text is None:
        await msg.reply("Текст сообщения пуст")
        return

    try:
        lesson_id = int(msg.text.split()[1])
        await redis.setex(f"cancel:{lesson_id}", 86400, "1")

        await msg.reply(
            f"✅ Урок #{lesson_id} отменён на сегодня\n\n"
            f"Напоминания не будут отправлены. "
            f"Завтра урок вернётся в расписание автоматически."
        )
    except (ValueError, IndexError):
        await msg.reply(
            "❌ Неверный формат команды.\n\n"
            "<b>Формат:</b> <code>/cancel [ID урока]</code>\n\n"
            "<b>Пример:</b> <code>/cancel 5</code>\n\n"
            "Посмотреть ID можно командой /list"
        )


@router.message(Command("update"))
async def on_update(msg: Message, schedule: Schedule) -> None:
    await msg.reply(
        "🚧 Команда в разработке\n\n"
        "Пока можно удалить урок через /delete и создать новый через /add"
    )


DAYS_RU = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


@router.my_chat_member()
async def on_bot_join(event: ChatMemberUpdated, redis: Redis, bot: Bot):
    if event.new_chat_member.status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
    ]:
        chat_title = event.chat.title or ""
        chat_id = event.chat.id

        try:
            group_n = extract_group_number(chat_title)
            await redis.set(f"group:{group_n}", str(chat_id))

            await bot.send_message(
                event.from_user.id, f"✅ Подключено к группе {group_n}!"
            )
        except ValueError:
            await bot.send_message(
                event.from_user.id, "⚠️ Назовите чат: 'Группа 1', 'Группа 2'"
            )
            await bot.leave_chat(chat_id)


def extract_group_number(title: str) -> str:
    maybe_number = re.search(r"[Гг]руппа\s+(\d+)", title)
    if not maybe_number:
        raise ValueError("Cannot extract number of group from '{title}'")
    return maybe_number.group(1)
