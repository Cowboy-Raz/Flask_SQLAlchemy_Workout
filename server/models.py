"""
SQLAlchemy models for the Workout Tracking API.

Three tables:
    exercises          - reusable exercise library (Exercise)
    workouts           - a single training session (Workout)
    workout_exercises  - join table holding reps / sets / duration (WorkoutExercise)

Data integrity is enforced in two layers:
    1. Table constraints  (NOT NULL, UNIQUE, CHECK) - enforced by the database itself.
    2. Model validations  (@validates)              - enforced in Python before a flush.
"""
from datetime import date

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import validates

# Naming convention keeps constraint names predictable so Alembic
# migrations (especially SQLite batch migrations) can find and alter them.
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})

db = SQLAlchemy(metadata=metadata)


# SQLite ignores foreign keys unless this pragma is switched on per connection.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


EXERCISE_CATEGORIES = ("strength", "cardio", "flexibility", "balance", "mobility")


class Exercise(db.Model):
    __tablename__ = "exercises"

    # Table constraints: name required + unique, category required,
    # and category limited to a known list at the database level.
    __table_args__ = (
        CheckConstraint(
            "category IN ('strength', 'cardio', 'flexibility', 'balance', 'mobility')",
            name="valid_category",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=False)
    equipment_needed = db.Column(db.Boolean, nullable=False, default=False)

    # An Exercise has many WorkoutExercises; deleting an exercise removes its join rows.
    workout_exercises = db.relationship(
        "WorkoutExercise", back_populates="exercise", cascade="all, delete-orphan"
    )
    # An Exercise has many Workouts through WorkoutExercises.
    workouts = association_proxy("workout_exercises", "workout")

    @validates("name")
    def validate_name(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Exercise name must be a non-empty string.")
        value = value.strip()
        if len(value) > 100:
            raise ValueError("Exercise name must be 100 characters or fewer.")
        return value

    @validates("category")
    def validate_category(self, key, value):
        if not isinstance(value, str):
            raise ValueError("Category must be a string.")
        value = value.strip().lower()
        if value not in EXERCISE_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(EXERCISE_CATEGORIES)}.")
        return value

    @validates("equipment_needed")
    def validate_equipment_needed(self, key, value):
        if not isinstance(value, bool):
            raise ValueError("equipment_needed must be true or false.")
        return value

    def __repr__(self):
        return f"<Exercise {self.id}: {self.name} ({self.category})>"


class Workout(db.Model):
    __tablename__ = "workouts"

    # Table constraints: date required, duration required and positive,
    # and capped at a realistic single-session length (8 hours).
    __table_args__ = (
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 480",
            name="duration_minutes_range",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    # A Workout has many WorkoutExercises; deleting a workout removes its join rows.
    workout_exercises = db.relationship(
        "WorkoutExercise", back_populates="workout", cascade="all, delete-orphan"
    )
    # A Workout has many Exercises through WorkoutExercises.
    exercises = association_proxy("workout_exercises", "exercise")

    @validates("date")
    def validate_date(self, key, value):
        if not isinstance(value, date):
            raise ValueError("Workout date must be a valid date.")
        return value

    @validates("duration_minutes")
    def validate_duration_minutes(self, key, value):
        # bool is a subclass of int, so exclude it explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("duration_minutes must be an integer.")
        if not 1 <= value <= 480:
            raise ValueError("duration_minutes must be between 1 and 480.")
        return value

    @validates("notes")
    def validate_notes(self, key, value):
        if value is not None and len(value) > 500:
            raise ValueError("Notes must be 500 characters or fewer.")
        return value

    def __repr__(self):
        return f"<Workout {self.id}: {self.date} ({self.duration_minutes} min)>"


class WorkoutExercise(db.Model):
    __tablename__ = "workout_exercises"

    # Table constraints: numbers can't be negative, and every entry must
    # record *something* - either reps + sets, or a timed duration.
    __table_args__ = (
        CheckConstraint("reps IS NULL OR reps > 0", name="reps_positive"),
        CheckConstraint("sets IS NULL OR sets > 0", name="sets_positive"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="duration_seconds_positive",
        ),
        CheckConstraint(
            "(reps IS NOT NULL AND sets IS NOT NULL) OR duration_seconds IS NOT NULL",
            name="has_volume",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id = db.Column(
        db.Integer, db.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    reps = db.Column(db.Integer)
    sets = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)

    # A WorkoutExercise belongs to a Workout and to an Exercise.
    workout = db.relationship("Workout", back_populates="workout_exercises")
    exercise = db.relationship("Exercise", back_populates="workout_exercises")

    @validates("reps", "sets", "duration_seconds")
    def validate_positive_int(self, key, value):
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be an integer.")
        if value <= 0:
            raise ValueError(f"{key} must be greater than 0.")
        return value

    def __repr__(self):
        return (
            f"<WorkoutExercise {self.id}: workout={self.workout_id} "
            f"exercise={self.exercise_id} sets={self.sets} reps={self.reps} "
            f"duration={self.duration_seconds}s>"
        )
