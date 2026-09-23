import os

# Point the app at an in-memory database before it is imported.
os.environ["DATABASE_URI"] = "sqlite://"

from datetime import date

import pytest

from app import app as flask_app
from models import Exercise, Workout, WorkoutExercise, db


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        db.create_all()
        squat = Exercise(name="Back Squat", category="strength", equipment_needed=True)
        plank = Exercise(name="Plank", category="balance", equipment_needed=False)
        workout = Workout(date=date(2026, 9, 14), duration_minutes=60, notes="Leg day")
        join = WorkoutExercise(workout=workout, exercise=squat, sets=5, reps=5)
        db.session.add_all([squat, plank, workout, join])
        db.session.commit()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
