from datetime import datetime, time
from typing import Annotated
from zoneinfo import ZoneInfo
import dateparser
from pydantic import BaseModel, BeforeValidator, computed_field

MSK = "Europe/Moscow"
UTC = "UTC"


def validate_day_of_week(value: int):
    if not 0 <= value <= 6:
        raise ValueError("Date must be in range 0 to 6")
    return value


DayOfWeek = Annotated[int, BeforeValidator(validate_day_of_week)]


class Lesson(BaseModel):
    group_n: str
    day: DayOfWeek
    start_time: time
    subject: str

    @classmethod
    def from_str(cls, data: str) -> "Lesson":
        if (parts := data.split(maxsplit=3)) and len(parts) == 4:
            group_n, day_str, time_str, subject = parts
            if not group_n.isnumeric():
                raise ValueError("Group number must be a number")
            parsed_day = dateparser.parse(
                day_str, languages=["ru"], settings={"PREFER_DATES_FROM": "future"}
            )
            if not parsed_day:
                raise ValueError("Unknown day")
            parsed_time = dateparser.parse(
                time_str,
                languages=["ru"],
                settings={
                    "PREFER_DATES_FROM": "future",
                    "TIMEZONE": MSK,
                    "TO_TIMEZONE": UTC,
                },
            )
            if not parsed_time:
                raise ValueError("Unknown time")
            return Lesson(
                group_n=group_n,
                day=parsed_day.weekday(),
                start_time=parsed_time.time(),
                subject=subject.strip(),
            )
        else:
            raise ValueError("In your data must be minimum 4 words after command")

    @computed_field
    @property
    def start_time_msk(self) -> str:
        """Время в МСК для отображения"""
        utc_dt = datetime.now(ZoneInfo(UTC)).replace(
            hour=self.start_time.hour, minute=self.start_time.minute
        )
        msk_dt = utc_dt.astimezone(ZoneInfo(MSK))
        return msk_dt.strftime("%H:%M")
