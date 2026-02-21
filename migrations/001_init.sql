CREATE TABLE lessons (
    id BIGSERIAL PRIMARY KEY,
    group_n VARCHAR(50) NOT NULL,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL,
    subject VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lessons_group_day ON lessons(group_n, day_of_week, start_time);
CREATE INDEX idx_lessons_day ON lessons(day_of_week);

COMMENT ON TABLE lessons IS 'Расписание занятий для групп';
COMMENT ON COLUMN lessons.day_of_week IS '0=Monday, 6=Sunday';
COMMENT ON COLUMN lessons.start_time IS 'Время начала урока в UTC';