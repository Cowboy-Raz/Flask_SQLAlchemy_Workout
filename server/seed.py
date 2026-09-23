#!/usr/bin/env python3
"""Reset the database and load example data for every model."""
from datetime import date

from app import app
from models import *  # noqa: F401,F403

with app.app_context():
    print("Clearing existing data...")
    # Delete children first so foreign keys are never left dangling.
    WorkoutExercise.query.delete()
    Workout.query.delete()
    Exercise.query.delete()
    db.session.commit()

    print("Seeding exercises...")
    squat = Exercise(name="Back Squat", category="strength", equipment_needed=True)
    pushup = Exercise(name="Push-Up", category="strength", equipment_needed=False)
    deadlift = Exercise(name="Deadlift", category="strength", equipment_needed=True)
    plank = Exercise(name="Plank", category="balance", equipment_needed=False)
    rower = Exercise(name="Rowing Machine", category="cardio", equipment_needed=True)
    hamstring = Exercise(name="Hamstring Stretch", category="flexibility", equipment_needed=False)
    exercises = [squat, pushup, deadlift, plank, rower, hamstring]

    print("Seeding workouts...")
    leg_day = Workout(
        date=date(2026, 9, 14), duration_minutes=60,
        notes="Lower body strength focus. Client hit a squat PR.",
    )
    upper_core = Workout(
        date=date(2026, 9, 16), duration_minutes=45,
        notes="Upper body and core. Keep push-up form strict.",
    )
    conditioning = Workout(
        date=date(2026, 9, 18), duration_minutes=30,
        notes="Conditioning plus cool-down stretching.",
    )
    workouts = [leg_day, upper_core, conditioning]

    print("Seeding workout exercises...")
    workout_exercises = [
        # Rep-based entries
        WorkoutExercise(workout=leg_day, exercise=squat, sets=5, reps=5),
        WorkoutExercise(workout=leg_day, exercise=deadlift, sets=3, reps=5),
        WorkoutExercise(workout=upper_core, exercise=pushup, sets=4, reps=15),
        # Timed entries
        WorkoutExercise(workout=upper_core, exercise=plank, duration_seconds=60),
        WorkoutExercise(workout=conditioning, exercise=rower, duration_seconds=900),
        WorkoutExercise(workout=conditioning, exercise=hamstring, duration_seconds=120),
        # Same exercise reused across workouts
        WorkoutExercise(workout=leg_day, exercise=hamstring, duration_seconds=90),
        # Both sets/reps and a time cap
        WorkoutExercise(workout=conditioning, exercise=pushup, sets=2, reps=20, duration_seconds=120),
    ]
    # Add everything at once, after relationships are wired up.
    db.session.add_all(exercises + workouts + workout_exercises)

    db.session.commit()
    print(
        f"Done! Seeded {len(exercises)} exercises, {len(workouts)} workouts, "
        f"and {len(workout_exercises)} workout exercises."
    )
