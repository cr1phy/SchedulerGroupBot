from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from pydantic import ValidationError

from models import Lesson, Schedule

router = Router()


@router.message(CommandStart())
async def on_start(msg: Message) -> None:
    await msg.answer("hello")


@router.message(Command("add"))
async def on_add(msg: Message, schedule: Schedule) -> None:
    if msg.text is None:
        await msg.reply("Message text is empty")
        return
    try:
        text = msg.text.split(maxsplit=1)[1]
        data = Lesson.from_str(text)
        await msg.answer(data.model_dump_json())
    except (ValidationError, IndexError) as e:
        await msg.reply(str(e))


@router.message(Command("update"))
async def on_update() -> None:
    pass


@router.message(Command("delete"))
async def on_delete() -> None:
    pass


@router.message(Command("list"))
async def on_list() -> None:
    pass
