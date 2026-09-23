"""
Flask application + routes for the Workout Tracking API.

Run from the server/ directory:
    flask run            (FLASK_APP defaults to app.py)
    python app.py        (serves on port 5555)
"""
import os

from flask import Flask, jsonify, make_response, request
from flask_migrate import Migrate
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from models import *  # noqa: F401,F403  (db, Exercise, Workout, WorkoutExercise)
from schemas import (
    exercise_detail_schema,
    exercise_schema,
    exercises_schema,
    workout_detail_schema,
    workout_exercise_detail_schema,
    workout_exercise_schema,
    workout_schema,
    workouts_schema,
)

app = Flask(__name__)
# DATABASE_URI lets tests swap in an in-memory database.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.sort_keys = False

migrate = Migrate(app, db)

db.init_app(app)


# ---------- Helpers ----------

def error_response(message, status, details=None):
    """Consistent error envelope: {"error": ..., "details": ...}."""
    body = {"error": message}
    if details is not None:
        body["details"] = details
    return make_response(jsonify(body), status)


def get_json_body():
    """Return the request JSON as a dict, or None if missing/malformed."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


# ---------- Error handlers ----------

@app.errorhandler(404)
def not_found(e):
    return error_response("Resource not found.", 404)


@app.errorhandler(405)
def method_not_allowed(e):
    return error_response("Method not allowed.", 405)


# ---------- Workouts ----------

@app.route("/workouts", methods=["GET"])
def get_workouts():
    workouts = Workout.query.order_by(Workout.date.desc()).all()
    return make_response(jsonify(workouts_schema.dump(workouts)), 200)


@app.route("/workouts/<int:id>", methods=["GET"])
def get_workout(id):
    workout = db.session.get(Workout, id)
    if not workout:
        return error_response(f"Workout {id} not found.", 404)
    return make_response(jsonify(workout_detail_schema.dump(workout)), 200)


@app.route("/workouts", methods=["POST"])
def create_workout():
    data = get_json_body()
    if data is None:
        return error_response("Request body must be a JSON object.", 400)
    try:
        # Schema validation -> clean dict; model validation runs on assignment.
        workout = Workout(**workout_schema.load(data))
        db.session.add(workout)
        db.session.commit()
    except ValidationError as err:
        return error_response("Validation failed.", 400, err.messages)
    except ValueError as err:
        db.session.rollback()
        return error_response(str(err), 400)
    except IntegrityError:
        db.session.rollback()
        return error_response("Workout violates a database constraint.", 400)
    return make_response(jsonify(workout_detail_schema.dump(workout)), 201)


@app.route("/workouts/<int:id>", methods=["DELETE"])
def delete_workout(id):
    workout = db.session.get(Workout, id)
    if not workout:
        return error_response(f"Workout {id} not found.", 404)
    # cascade="all, delete-orphan" also removes its WorkoutExercises.
    db.session.delete(workout)
    db.session.commit()
    return make_response("", 204)


# ---------- Exercises ----------

@app.route("/exercises", methods=["GET"])
def get_exercises():
    exercises = Exercise.query.order_by(Exercise.name).all()
    return make_response(jsonify(exercises_schema.dump(exercises)), 200)


@app.route("/exercises/<int:id>", methods=["GET"])
def get_exercise(id):
    exercise = db.session.get(Exercise, id)
    if not exercise:
        return error_response(f"Exercise {id} not found.", 404)
    return make_response(jsonify(exercise_detail_schema.dump(exercise)), 200)


@app.route("/exercises", methods=["POST"])
def create_exercise():
    data = get_json_body()
    if data is None:
        return error_response("Request body must be a JSON object.", 400)
    try:
        exercise = Exercise(**exercise_schema.load(data))
        db.session.add(exercise)
        db.session.commit()
    except ValidationError as err:
        return error_response("Validation failed.", 400, err.messages)
    except ValueError as err:
        db.session.rollback()
        return error_response(str(err), 400)
    except IntegrityError:
        # Most likely the UNIQUE constraint on name.
        db.session.rollback()
        return error_response("An exercise with that name already exists.", 409)
    return make_response(jsonify(exercise_schema.dump(exercise)), 201)


@app.route("/exercises/<int:id>", methods=["DELETE"])
def delete_exercise(id):
    exercise = db.session.get(Exercise, id)
    if not exercise:
        return error_response(f"Exercise {id} not found.", 404)
    # cascade="all, delete-orphan" also removes its WorkoutExercises.
    db.session.delete(exercise)
    db.session.commit()
    return make_response("", 204)


# ---------- WorkoutExercises (join) ----------

@app.route(
    "/workouts/<int:workout_id>/exercises/<int:exercise_id>/workout_exercises",
    methods=["POST"],
)
def add_exercise_to_workout(workout_id, exercise_id):
    workout = db.session.get(Workout, workout_id)
    if not workout:
        return error_response(f"Workout {workout_id} not found.", 404)
    exercise = db.session.get(Exercise, exercise_id)
    if not exercise:
        return error_response(f"Exercise {exercise_id} not found.", 404)

    data = get_json_body()
    if data is None:
        return error_response("Request body must be a JSON object.", 400)
    try:
        workout_exercise = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercise.id,
            **workout_exercise_schema.load(data),
        )
        db.session.add(workout_exercise)
        db.session.commit()
    except ValidationError as err:
        return error_response("Validation failed.", 400, err.messages)
    except ValueError as err:
        db.session.rollback()
        return error_response(str(err), 400)
    except IntegrityError:
        db.session.rollback()
        return error_response("Workout exercise violates a database constraint.", 400)
    return make_response(jsonify(workout_exercise_detail_schema.dump(workout_exercise)), 201)


if __name__ == "__main__":
    app.run(port=5555, debug=True)
