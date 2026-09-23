"""
Marshmallow schemas for serialization (model -> JSON) and
deserialization + validation (request JSON -> clean dict).

Nesting is one level deep in each direction to avoid infinite recursion:
    Workout  -> workout_exercises -> exercise
    Exercise -> workout_exercises -> workout
"""
from marshmallow import Schema, ValidationError, fields, validate, validates, validates_schema

from models import EXERCISE_CATEGORIES


# ---------- Exercise ----------

class ExerciseSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100, error="Name must be 1-100 characters."),
    )
    category = fields.Str(
        required=True,
        validate=validate.OneOf(
            EXERCISE_CATEGORIES,
            error="Category must be one of: " + ", ".join(EXERCISE_CATEGORIES) + ".",
        ),
    )
    equipment_needed = fields.Bool(load_default=False)

    @validates("name")
    def validate_name_not_blank(self, value):
        if not value.strip():
            raise ValidationError("Name cannot be blank.")


# ---------- Workout ----------

class WorkoutSchema(Schema):
    id = fields.Int(dump_only=True)
    date = fields.Date(required=True)  # ISO format: YYYY-MM-DD
    duration_minutes = fields.Int(
        required=True,
        strict=True,
        validate=validate.Range(min=1, max=480, error="duration_minutes must be between 1 and 480."),
    )
    notes = fields.Str(
        allow_none=True,
        load_default=None,
        validate=validate.Length(max=500, error="Notes must be 500 characters or fewer."),
    )


# ---------- WorkoutExercise (join) ----------

class WorkoutExerciseSchema(Schema):
    id = fields.Int(dump_only=True)
    workout_id = fields.Int(dump_only=True)
    exercise_id = fields.Int(dump_only=True)
    reps = fields.Int(
        strict=True, allow_none=True, load_default=None,
        validate=validate.Range(min=1, error="reps must be at least 1."),
    )
    sets = fields.Int(
        strict=True, allow_none=True, load_default=None,
        validate=validate.Range(min=1, error="sets must be at least 1."),
    )
    duration_seconds = fields.Int(
        strict=True, allow_none=True, load_default=None,
        validate=validate.Range(min=1, error="duration_seconds must be at least 1."),
    )

    @validates_schema
    def validate_has_volume(self, data, **kwargs):
        """Require reps + sets together, or a duration (or both)."""
        reps, sets, duration = data.get("reps"), data.get("sets"), data.get("duration_seconds")
        if (reps is None) != (sets is None):
            raise ValidationError("reps and sets must be provided together.", "reps")
        if reps is None and duration is None:
            raise ValidationError(
                "Provide reps and sets, or duration_seconds.", "_schema"
            )


# ---------- Nested / detail schemas ----------

class WorkoutExerciseWithExerciseSchema(WorkoutExerciseSchema):
    """Join row as seen from a Workout: shows the exercise it points to."""
    exercise = fields.Nested(ExerciseSchema, dump_only=True)


class WorkoutExerciseWithWorkoutSchema(WorkoutExerciseSchema):
    """Join row as seen from an Exercise: shows the workout it belongs to."""
    workout = fields.Nested(WorkoutSchema, dump_only=True)


class WorkoutDetailSchema(WorkoutSchema):
    """Single workout with its exercises and reps/sets/duration (stretch goal)."""
    workout_exercises = fields.List(
        fields.Nested(WorkoutExerciseWithExerciseSchema), dump_only=True
    )


class ExerciseDetailSchema(ExerciseSchema):
    """Single exercise with the workouts it appears in."""
    workout_exercises = fields.List(
        fields.Nested(WorkoutExerciseWithWorkoutSchema), dump_only=True
    )


# ---------- Schema instances ----------

exercise_schema = ExerciseSchema()
exercises_schema = ExerciseSchema(many=True)
exercise_detail_schema = ExerciseDetailSchema()

workout_schema = WorkoutSchema()
workouts_schema = WorkoutSchema(many=True)
workout_detail_schema = WorkoutDetailSchema()

workout_exercise_schema = WorkoutExerciseSchema()
workout_exercise_detail_schema = WorkoutExerciseWithExerciseSchema()
