from datetime import time

from app.models import Lesson

def test_parsing_lesson():
    assert Lesson.from_str("Пн 10:00 Боталка 19-ого номера") == Lesson(
        day=0,
        start_time=time(hour=10, minute=0, second=0),
        subject="Боталка 19-ого номера",
    )
