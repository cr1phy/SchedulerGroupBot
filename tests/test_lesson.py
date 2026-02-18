from datetime import time
import pytest
from app.models import Lesson


def test_successful_parsing_lesson():
    assert Lesson.from_str("1 Пн 10:00 Боталка 19-ого номера") == Lesson(
        group_n="1",
        day=0,
        start_time=time(hour=10, minute=0, second=0),
        subject="Боталка 19-ого номера",
    )


@pytest.mark.parametrize("text", ["ВC", "22:30", "ВС 23:59"])
def test_validation_parts_error(text: str):
    """Test invalid number of parts (< 3)"""
    with pytest.raises(ValueError) as exc:
        Lesson.from_str(text)
    assert "minimum 3 words" in str(exc.value)


@pytest.mark.parametrize(
    "text", ["?? 23:49 ИНФО", "ВТ 24:01 _", "читверг -10:00 _", "чт 10:128 _"]
)
def test_parsing_incorrect_date_or_time(text: str):
    """Test invalid day/time format"""
    with pytest.raises(ValueError) as exc:
        Lesson.from_str(text)
    assert "Unknown" in str(exc.value)
