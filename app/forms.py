from pydantic import BaseModel
from datetime import time

from app.models import Lesson


class LessonPartial(BaseModel):
    day: int | None = None
    start_time: time | None = None
    subject: str | None = None


class AddLesson(BaseModel):
    lesson: Lesson


class UpdateLesson(BaseModel):
    lesson_id: int
    lesson: LessonPartial


class DeleteLesson(BaseModel):
    lesson_id: int


class CancelLesson(BaseModel):
    lesson_id: int
