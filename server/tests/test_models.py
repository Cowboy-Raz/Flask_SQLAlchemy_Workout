"""Model validations (@validates) and table constraints (database level)."""
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models import Exercise, Workout, WorkoutExercise, db


class TestModelValidations:
    def test_exercise_name_cannot_be_blank(self, app):
        with pytest.raises(ValueError):
            Exercise(name="   ", category="strength")

    def test_exercise_category_must_be_known(self, app):
        with pytest.raises(ValueError):
            Exercise(name="Mystery Move", category="dance")

    def test_exercise_category_is_normalized(self, app):
        assert Exercise(name="Lunge", category=" Strength ").category == "strength"

    def test_workout_duration_must_be_in_range(self, app):
        with pytest.raises(ValueError):
            Workout(date=date(2026, 1, 1), duration_minutes=0)
        with pytest.raises(ValueError):
            Workout(date=date(2026, 1, 1), duration_minutes=481)

    def test_workout_date_must_be_a_date(self, app):
        with pytest.raises(ValueError):
            Workout(date="2026-01-01", duration_minutes=30)

    def test_workout_notes_length(self, app):
        with pytest.raises(ValueError):
            Workout(date=date(2026, 1, 1), duration_minutes=30, notes="x" * 501)

    def test_workout_exercise_values_must_be_positive(self, app):
        with pytest.raises(ValueError):
            WorkoutExercise(reps=-1)
        with pytest.raises(ValueError):
            WorkoutExercise(duration_seconds=0)


class TestTableConstraints:
    """Raw SQL bypasses model validations, proving the database enforces these."""

    def test_exercise_name_is_unique(self, app):
        db.session.add(Exercise(name="Back Squat", category="strength"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_exercise_category_check(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(text(
                "INSERT INTO exercises (name, category, equipment_needed) "
                "VALUES ('Bad', 'dance', 0)"
            ))
        db.session.rollback()

    def test_workout_duration_check(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(text(
                "INSERT INTO workouts (date, duration_minutes) VALUES ('2026-01-01', -5)"
            ))
        db.session.rollback()

    def test_workout_date_not_null(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(text("INSERT INTO workouts (duration_minutes) VALUES (30)"))
        db.session.rollback()

    def test_workout_exercise_requires_volume(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(text(
                "INSERT INTO workout_exercises (workout_id, exercise_id) VALUES (1, 1)"
            ))
        db.session.rollback()

    def test_workout_exercise_foreign_keys(self, app):
        with pytest.raises(IntegrityError):
            db.session.execute(text(
                "INSERT INTO workout_exercises (workout_id, exercise_id, duration_seconds) "
                "VALUES (999, 999, 30)"
            ))
        db.session.rollback()


class TestRelationships:
    def test_workout_has_many_exercises_through_join(self, app):
        workout = db.session.get(Workout, 1)
        assert [e.name for e in workout.exercises] == ["Back Squat"]

    def test_exercise_has_many_workouts_through_join(self, app):
        exercise = Exercise.query.filter_by(name="Back Squat").first()
        assert exercise.workouts[0].notes == "Leg day"

    def test_deleting_workout_deletes_join_rows(self, app):
        db.session.delete(db.session.get(Workout, 1))
        db.session.commit()
        assert WorkoutExercise.query.count() == 0
        assert Exercise.query.count() == 2  # exercises survive
