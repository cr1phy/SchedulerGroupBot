from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial
from typing import Callable, Any

from aiogram import Bot
from redis.asyncio import Redis
from app.dao import LessonDAO
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore
from apscheduler.jobstores.base import JobLookupError # type: ignore
from app.forms import AddLesson, DeleteLesson, UpdateLesson
from app.models import Lesson
from app.reminders import (
    send_homework_reminder,
    send_lesson_reminder,
    send_payment_reminder,
)


@dataclass
class Schedule:
    _dao: LessonDAO
    _scheduler: AsyncIOScheduler = field(default_factory=AsyncIOScheduler)
    _lessons: dict[int, Lesson] = field(default_factory=dict[int, Lesson])
    _lesson_reminder: Callable[..., Any] | None = field(default=None)
    _homework_reminder: Callable[..., Any] | None = field(default=None)
    _payment_reminder: Callable[..., Any] | None = field(default=None)

    def start(self) -> None:
        self._scheduler.start()

    async def load(self) -> None:
        lessons = await self._dao.get_all()
        for lesson_id, lesson in lessons:
            self._lessons[lesson_id] = lesson
            self._add_job(lesson_id, lesson)

    def setup_reminders(self, bot: Bot, redis: Redis) -> None:
        self._lesson_reminder = partial(send_lesson_reminder, bot, redis)
        self._homework_reminder = partial(send_homework_reminder, bot, redis)
        self._payment_reminder = partial(send_payment_reminder, bot, redis)

    def setup_payment_reminders(self) -> None:
        groups = set(lesson.group_n for lesson in self._lessons.values())

        for group_n in groups:
            self._scheduler.add_job(  # type: ignore
                self._payment_reminder,
                trigger="cron",
                day_of_week=0,
                hour=9,
                minute=0,
                id=f"payment_reminder_{group_n}",
                kwargs={"group_n": group_n},
            )

    def _add_job(self, lesson_id: int, lesson: Lesson) -> None:
        reminder_time = (
            datetime.combine(datetime.today(), lesson.start_time)
            - timedelta(minutes=30)
        ).time()

        self._scheduler.add_job(  # type: ignore
            self._lesson_reminder,
            trigger="cron",
            day_of_week=lesson.day,
            hour=reminder_time.hour,
            minute=reminder_time.minute,
            id=f"lesson_reminder_{lesson_id}",
            kwargs={"lesson_id": lesson_id, "lesson": lesson},
        )

        self._scheduler.add_job(  # type: ignore
            self._homework_reminder,
            trigger="cron",
            day_of_week=lesson.day,
            hour=8,
            minute=0,
            id=f"homework_reminder_{lesson_id}",
            kwargs={"lesson_id": lesson_id, "lesson": lesson},
        )

    async def get_all_lessons(self) -> list[tuple[int, Lesson]]:
        return list(self._lessons.items())

    def get_lesson(self, lesson_id: int) -> Lesson | None:
        return self._lessons.get(lesson_id)

    async def add(self, form: AddLesson) -> None:
        lesson_id = await self._dao.insert(form.lesson)
        self._add_job(lesson_id, form.lesson)
        self._lessons[lesson_id] = form.lesson

    async def update(self, form: UpdateLesson) -> bool:
        if form.lesson_id not in self._lessons:
            return False

        old_lesson = self._lessons[form.lesson_id]

        lesson: Lesson = old_lesson or form.lesson
        new_lesson = Lesson(
            group_n=lesson.group_n,
            day=lesson.day,
            start_time=lesson.start_time,
            subject=lesson.subject,
        )

        await self._dao.update(form.lesson_id, new_lesson)

        for job_type in ["lesson_reminder", "homework_reminder"]:
            try:
                self._scheduler.remove_job(f"{job_type}_{form.lesson_id}")  # type: ignore
            except JobLookupError:
                pass

        self._add_job(form.lesson_id, new_lesson)
        self._lessons[form.lesson_id] = new_lesson
        return True

    async def delete(self, form: DeleteLesson) -> bool:
        if form.lesson_id not in self._lessons:
            return False

        await self._dao.delete(form.lesson_id)

        for job_type in ["lesson_reminder", "homework_reminder"]:
            try:
                self._scheduler.remove_job(f"{job_type}_{form.lesson_id}")  # type: ignore
            except JobLookupError:
                pass

        del self._lessons[form.lesson_id]
        return True
