from dataclasses import dataclass, field
from datetime import time
from typing import Annotated
from apscheduler.job import Job  # type: ignore[import]
import dateparser
from pydantic import BaseModel, BeforeValidator
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import]

from app.dao import LessonDAO  # type: ignore[import]
from app.forms import AddLesson, DeleteLesson, UpdateLesson


def validate_day_of_week(value: int):
    if not 0 <= value <= 6:
        raise ValueError("Date must be in range 0 to 6")
    return value


DayOfWeek = Annotated[int, BeforeValidator(validate_day_of_week)]


class Lesson(BaseModel):
    day: DayOfWeek
    start_time: time
    subject: str

    @classmethod
    def from_str(cls, data: str) -> "Lesson":
        if (parts := data.split(maxsplit=2)) and len(parts) == 3:
            day_str, time_str, subject = parts
            parsed_day = dateparser.parse(
                day_str, languages=["ru"], settings={"PREFER_DATES_FROM": "future"}
            )
            if not parsed_day:
                raise ValueError("Unknown day")
            parsed_time = dateparser.parse(
                time_str, languages=["ru"], settings={"PREFER_DATES_FROM": "future"}
            )
            if not parsed_time:
                raise ValueError("Unknown time")
            return Lesson(
                day=parsed_day.weekday(),
                start_time=parsed_time.time(),
                subject=subject.strip(),
            )
        else:
            raise ValueError("In your data must be minimum 3 words after command")


@dataclass
class Schedule:
    _dao: LessonDAO
    _scheduler: AsyncIOScheduler = field(default_factory=AsyncIOScheduler)
    _lessons: dict[int, Lesson] = field(default_factory=dict[int, Lesson])
    _jobs: dict[int, Job] = field(default_factory=dict[int, Job])

    def start(self) -> None:
        self._scheduler.start()

    async def load(self) -> None:
        lessons = await self._dao.get_all()
        for lesson_id, lesson in lessons:
            self._lessons[lesson_id] = lesson
            self._add_job(lesson_id, lesson)

    def _add_job(self, lesson_id: int, lesson: Lesson) -> Job:
        return self._scheduler.add_job(
            _,
            trigger="cron",
            day_of_week=lesson.day,
            hour=lesson.start_time.hour,
            minute=lesson.start_time.minute,
            id=f"lesson_{lesson_id}",
            args=[lesson_id],
        )

    async def add(self, form: AddLesson) -> Job:
        lesson_id = await self._dao.insert(form.lesson)
        job = self._add_job(lesson_id, form.lesson)

        self._lessons[lesson_id] = form.lesson
        self._jobs[lesson_id] = job

        return job

    async def update(self, form: UpdateLesson) -> bool:
        if form.lesson_id not in self._lessons:
            return False

        old_lesson = self._lessons[form.lesson_id]

        lesson: Lesson = form.lesson or old_lesson
        new_lesson = Lesson(
            day=lesson.day,
            start_time=lesson.start_time,
            subject=lesson.subject,
        )

        await self._dao.update(form.lesson_id, new_lesson)

        self._scheduler.remove_job(f"lesson_{form.lesson_id}")
        job = self._add_job(form.lesson_id, new_lesson)

        self._lessons[form.lesson_id] = new_lesson
        self._jobs[form.lesson_id] = job
        return True

    async def delete(self, form: DeleteLesson) -> bool:
        if form.lesson_id not in self._lessons:
            return False

        await self._dao.delete(form.lesson_id)
        self._scheduler.remove_job(f"lesson_{form.lesson_id}")  # type: ignore

        del self._lessons[form.lesson_id]
        del self._jobs[form.lesson_id]
        return True
