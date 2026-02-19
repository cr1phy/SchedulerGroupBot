import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode, UpdateType
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.client.default import DefaultBotProperties
from os import getenv
from dotenv import load_dotenv
from redis.asyncio import from_url
import structlog
from app.dao import LessonDAO
from app.middlewares import LoggingMiddleware, OnlyOwnerMiddleware
from app.router import router
from app.schedule import Schedule

load_dotenv()


def get_required_envvar(key: str) -> str:
    if var := getenv(key):
        return var
    else:
        raise RuntimeError(f"{key} is not found in .env!")


BOT_TOKEN = get_required_envvar("BOT_TOKEN")
DATABASE_URL = get_required_envvar("DATABASE_URL")
REDIS_URL = get_required_envvar("REDIS_URL")
OWNER_TGID = int(get_required_envvar("OWNER_TGID"))
PAYMENT_LINK = getenv("PAYMENT_LINK", "")


async def set_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="add", description="Добавить урок"),
        BotCommand(command="list", description="Показать расписание"),
        BotCommand(command="delete", description="Удалить урок"),
        BotCommand(command="cancel", description="Отменить урок"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=OWNER_TGID))


async def main() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(),
        ]
    )

    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        with open("migrations/001_init.sql") as f:
            await conn.execute(f.read())

    redis = await from_url(REDIS_URL)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(OnlyOwnerMiddleware(OWNER_TGID))
    dp.include_router(router)

    dao = LessonDAO(pool)
    schedule = Schedule(dao)
    schedule.start()
    schedule.setup_reminders(bot, redis, PAYMENT_LINK)
    schedule.setup_payment_reminders()
    await schedule.load()

    await set_commands(bot)
    await dp.start_polling(  # type: ignore
        bot,
        schedule=schedule,
        redis=redis,
        allowed_updates=[
            UpdateType.MESSAGE,
            UpdateType.CHAT_JOIN_REQUEST,
            UpdateType.MY_CHAT_MEMBER,
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
