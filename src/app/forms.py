from pydantic import BaseModel, create_model, Field

from app.models import Lesson

LessonPartial = create_model(  # type: ignore
    model_name="LessonPartial",
    **{
        k: (v.annotation, Field(default=None))
        for (k, v) in Lesson.model_fields.items()
        if k != "id"
    },
)


class AddLesson(BaseModel):
    lesson: Lesson


class UpdateLesson(BaseModel):
    lesson_id: int
    lesson: LessonPartial  # type: ignore


class DeleteLesson(BaseModel):
    lesson_id: int
