from asyncpg import Pool, Record  # type: ignore[import]

from app.models import Lesson


class LessonDAO:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def insert(self, lesson: Lesson) -> int:
        return await self._pool.fetchval(  # type: ignore
            "INSERT INTO lessons (group_n, day_of_week, start_time, subject) VALUES ($1, $2, $3, $4) RETURNING id",
            lesson.group_n,
            lesson.day,
            lesson.start_time,
            lesson.subject,
        )

    async def get_all(self) -> list[tuple[int, Lesson]]:
        rows: list[Record] = await self._pool.fetch("SELECT * FROM lessons")  # type: ignore
        return [
            (
                row["id"],
                Lesson(
                    group_n=row["group_n"],
                    day=row["day_of_week"],
                    start_time=row["start_time"],
                    subject=row["subject"],
                ),
            )
            for row in rows
        ]

    async def update(self, lesson_id: int, new_lesson: Lesson) -> None:
        await self._pool.execute(  # type: ignore
            "UPDATE lessons SET group_n=$1, day_of_week=$2, start_time=$3, subject=$4 WHERE id=$5",
            new_lesson.group_n,
            new_lesson.day,
            new_lesson.start_time,
            new_lesson.subject,
            lesson_id,
        )

    async def delete(self, lesson_id: int) -> None:
        await self._pool.execute(  # type: ignore
            "DELETE FROM lessons WHERE id=$1",
            lesson_id,
        )
