from aiogram import Bot
from redis.asyncio import Redis

from app.schedule import Schedule

LESSON_REMINDER_TEXT = (
    "⏰ <b>Напоминание о занятии</b>\n\n"
    "Через 30 минут начнётся урок:\n"
    "<b>{subject}</b>\n\n"
    "Время начала: {time}"
)

HOMEWORK_REMINDER_TEXT = (
    "📝 <b>Дедлайн домашнего задания</b>\n\n"
    "Сегодня в {time} занятие по предмету:\n"
    "<b>{subject}</b>\n\n"
    "Не забудьте сдать домашнее задание до начала урока!"
)

PAYMENT_REMINDER_TEXT = (
    "💰 <b>Напоминание об оплате</b>\n\n"
    "Не забудьте внести оплату за занятия на этой неделе.\n\n"
    "Спасибо за своевременную оплату! 🙏"
)


async def send_lesson_reminder(
    bot: Bot, redis: Redis, schedule: Schedule, lesson_id: int
) -> None:
    """За 30 минут до занятия"""
    if await redis.get(f"cancel:{lesson_id}"):
        await redis.delete(f"cancel:{lesson_id}")
        return

    lesson = schedule.get_lesson(lesson_id)
    if not lesson:
        return

    chat_id = await redis.get(f"group:{lesson.group_n}")
    if not chat_id:
        return

    await bot.send_message(
        chat_id=chat_id,
        text=LESSON_REMINDER_TEXT.format(
            subject=lesson.subject, time=lesson.start_time
        ),
    )


async def send_homework_reminder(
    bot: Bot, chat_id: int, subject: str, time: str
) -> None:
    """Утром в день занятия - напоминание про дедлайн к ДЗ"""
    await bot.send_message(
        chat_id=chat_id,
        text=HOMEWORK_REMINDER_TEXT.format(subject=subject, time=time),
    )


async def send_payment_reminder(bot: Bot, redis: Redis, group_n: str) -> None:
    """Каждый понедельник - напоминание об оплате"""
    chat_id = await redis.get(f"group:{group_n}")
    if not chat_id:
        return
    
    await bot.send_message(chat_id=chat_id, text=PAYMENT_REMINDER_TEXT)
