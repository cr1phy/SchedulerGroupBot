from aiogram import Bot
from redis.asyncio import Redis
from app.models import Lesson

LESSON_REMINDER_TEXT = (
    "⏰ <b>Напоминание о занятии</b>\n\n"
    "Через 30 минут начнётся урок:\n"
    "<b>{subject}</b>\n"
    "Время начала: {time}"
)

HOMEWORK_REMINDER_TEXT = (
    "📝 <b>Дедлайн домашнего задания</b>\n\n"
    "Сегодня в {time} занятие: <b>{subject}</b>\n"
    "Не забудьте сдать домашнее задание до начала урока!"
)

PAYMENT_REMINDER_TEXT = (
    "💰 <b>Напоминание об оплате</b>\n\n"
    "Не забудьте внести оплату за занятия на этой неделе.\n"
    "Спасибо за своевременную оплату! 🙏"
)


async def send_lesson_reminder(
    bot: Bot,
    redis: Redis,
    lesson_id: int,
    lesson: Lesson,
) -> None:
    """За 30 минут до занятия"""
    if await redis.get(f"cancel:{lesson_id}"):
        await redis.delete(f"cancel:{lesson_id}")
        return

    chat_id = await redis.get(f"group:{lesson.group_n}")
    if not chat_id:
        return

    await bot.send_message(
        int(chat_id), f"⏰ Через 30 минут урок:\n<b>{lesson.subject}</b>"
    )


async def send_homework_reminder(
    bot: Bot,
    redis: Redis,
    lesson_id: int,
    lesson: Lesson,
) -> None:
    """Утром в день занятия"""
    if await redis.get(f"cancel:{lesson_id}"):
        return

    chat_id = await redis.get(f"group:{lesson.group_n}")
    if not chat_id:
        return

    await bot.send_message(
        int(chat_id),
        text=HOMEWORK_REMINDER_TEXT.format(
            subject=lesson.subject, time=lesson.start_time_msk
        ),
    )


async def send_payment_reminder(bot: Bot, redis: Redis, group_n: str) -> None:
    """Каждый понедельник - напоминание об оплате"""
    chat_id = await redis.get(f"group:{group_n}")
    if not chat_id:
        return

    await bot.send_message(chat_id=chat_id, text=PAYMENT_REMINDER_TEXT)
