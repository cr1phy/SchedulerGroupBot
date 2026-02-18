import asyncio
import asyncpg # type: ignore[import]
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from os import getenv
from dotenv import load_dotenv
import structlog
from app.dao import LessonDAO
from middlewares import LoggingMiddleware, OnlyOwnerMiddleware
from router import router
from models import Schedule

load_dotenv()


def get_required_envvar(key: str) -> str:
    if var := getenv(key):
        return var
    else:
        raise RuntimeError(f"{key} is not found in .env!")


BOT_TOKEN = get_required_envvar("BOT_TOKEN")
DATABASE_URL = get_required_envvar("DATABASE_URL")
OWNER_TGID: int = int(get_required_envvar("OWNER_TGID"))


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

    pool = await asyncpg.create_pool(DATABASE_URL)  # type: ignore
    dao = LessonDAO(pool)
    schedule = Schedule(dao)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(OnlyOwnerMiddleware(OWNER_TGID))
    dp.include_router(router)

    schedule.start()
    await schedule.load()

    await dp.start_polling(bot, schedule=schedule)  # type: ignore


if __name__ == "__main__":
    asyncio.run(main())
