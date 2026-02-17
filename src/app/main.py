import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from os import getenv
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import structlog
from middlewares import LoggingMiddleware
from router import router
from models import Schedule

load_dotenv()


def get_required_envvar(key: str) -> str:
    if var := getenv(key):
        return var
    else:
        raise RuntimeError(f"{key} is not found in .env!")


BOT_TOKEN = get_required_envvar("BOT_TOKEN")


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

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.start()

    await dp.start_polling(bot, schedule=Schedule(scheduler))  # type: ignore


if __name__ == "__main__":
    asyncio.run(main())
