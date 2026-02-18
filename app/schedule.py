from dataclasses import dataclass, field
from app.dao import LessonDAO
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.job import Job  # type: ignore
from app.forms import AddLesson, DeleteLesson, UpdateLesson
from app.models import Lesson
from app.reminders import send_lesson_reminder


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
        return self._scheduler.add_job(  # type: ignore
            send_lesson_reminder,
            trigger="cron",
            day_of_week=lesson.day,
            hour=lesson.start_time.hour,
            minute=lesson.start_time.minute,
            id=f"lesson_{lesson_id}",
            args=[lesson_id],
        )

    async def get_all_lessons(self) -> list[tuple[int, Lesson]]:
        return list(self._lessons.items())

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

        lesson: Lesson = old_lesson or form.lesson
        new_lesson = Lesson(
            group_n=lesson.group_n,
            day=lesson.day,
            start_time=lesson.start_time,
            subject=lesson.subject,
        )

        await self._dao.update(form.lesson_id, new_lesson)

        self._scheduler.remove_job(f"lesson_s{form.lesson_id}")  # type: ignore
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
