from datetime import time
from typing import Annotated, TYPE_CHECKING
from apscheduler.job import Job  # type: ignore[import]
import dateparser
from pydantic import BaseModel, BeforeValidator
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import]

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


class Schedule:
    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        self._scheduler = scheduler
        self._lessons: dict[int, Lesson] = {}
        self._jobs: dict[int, Job] = {}

    async def add(self, form: "AddLesson") -> Job:
        from app.forms import AddLesson

        return Job()

    async def update(self, form: "UpdateLesson") -> bool:
        from app.forms import UpdateLesson

        return True

    async def delete(self, form: "DeleteLesson") -> bool:
        from app.forms import DeleteLesson

        return True
