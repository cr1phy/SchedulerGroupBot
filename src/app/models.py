from dataclasses import dataclass, field
from datetime import time
from typing import Annotated, TYPE_CHECKING
from apscheduler.job import Job  # type: ignore[import]
import dateparser
from pydantic import BaseModel, BeforeValidator
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore[import]

from app.dao import LessonDAO  # type: ignore[import]

if TYPE_CHECKING:
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

    async def add(self, form: AddLesson) -> Job:
        lesson_id = await self._dao.insert(form.lesson)
        job = Job(self._scheduler, lesson_id)
        self._lessons[lesson_id] = form.lesson
        return job

    async def update(self, form: "UpdateLesson") -> bool:

        return True

    async def delete(self, form: "DeleteLesson") -> bool:

        return True
