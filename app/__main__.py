import asyncio
import asyncpg
import structlog
import re
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode, UpdateType
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.client.default import DefaultBotProperties
from os import getenv
from dotenv import load_dotenv
from redis.asyncio import from_url
from app.dao import LessonDAO
from app.middlewares import LoggingMiddleware, OnlyOwnerMiddleware
from app.router import router
from app.schedule import Schedule
from pathlib import Path

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


async def apply_migrations(pool: asyncpg.Pool) -> None:
    """Автоматически применяет SQL миграции из папки migrations/"""

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """
        )

        current_version = await conn.fetchval(
            "SELECT COALESCE(MAX(version), 0) FROM schema_version"
        )

        migrations_dir = Path("migrations")
        migration_files = sorted(
            migrations_dir.glob("*.sql"),
            key=lambda f: int(
                matches.group(1) if (matches := re.match(r"^(\d+)_", f.name)) else ""
            ),
        )

        for migration_file in migration_files:
            match = re.match(r"^(\d+)_", migration_file.name)
            if not match:
                continue

            version = int(match.group(1))

            if version <= current_version:
                continue

            print(f"Applying migration {version}: {migration_file.name}")

            with open(migration_file) as f:
                sql = f.read()
                await conn.execute(sql)

            await conn.execute(
                "INSERT INTO schema_version (version, filename) VALUES ($1, $2)",
                version,
                migration_file.name,
            )

            print(f"✅ Migration {version} applied")


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
    await apply_migrations(pool)

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
    await schedule.load()
    schedule.setup_payment_reminders()

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
