# Workout Tracker API

A Flask + SQLAlchemy + Marshmallow backend for a workout tracking application used by personal trainers. Trainers can build a reusable library of exercises, log workouts, and attach exercises to workouts with sets, reps, and/or a timed duration.

## Features

- **Three related models:** `Exercise`, `Workout`, and a `WorkoutExercise` join table that stores reps, sets, and duration.
- **Many-to-many relationships:** a workout has many exercises through `WorkoutExercise`, and an exercise has many workouts through `WorkoutExercise`.
- **Three layers of validation:**
  - **Table constraints (database):** `NOT NULL`, `UNIQUE` exercise names, `CHECK` constraints on category, workout duration (1-480 minutes), positive reps/sets/duration, and a rule that every workout exercise records reps + sets or a duration. Foreign keys are enforced in SQLite.
  - **Model validations (`@validates`):** non-blank names, known categories (normalized to lowercase), boolean `equipment_needed`, valid dates, duration range, 500-character notes limit, and positive integers on the join table.
  - **Schema validations (Marshmallow):** required fields, length, range, and `OneOf` validators, strict integers, plus a schema-level rule that reps and sets come together or a duration is given.
- **Cascading deletes:** deleting a workout or an exercise also deletes its `WorkoutExercise` rows.
- **Consistent JSON errors:** every error returns `{"error": "...", "details": {...}}` with the right status code.

## Project Structure

```
.
├── Pipfile               # dependencies
├── pytest.ini            # test configuration
├── README.md
└── server/
    ├── app.py            # Flask app, config, and routes
    ├── models.py         # SQLAlchemy models, relationships, constraints, validations
    ├── schemas.py        # Marshmallow schemas and schema validations
    ├── seed.py           # resets and seeds example data
    ├── migrations/       # Flask-Migrate / Alembic migrations
    └── tests/            # pytest suite for models and routes
```

## Installation

Requires Python 3.8.13+ and [Pipenv](https://pipenv.pypa.io/).

```bash
git clone <your-repo-url>
cd <repo-folder>

pipenv install --dev      # installs packages from the Pipfile (--dev adds pytest)
pipenv shell
```

Create the database and load example data:

```bash
cd server
export FLASK_APP=app.py
flask db upgrade head     # builds app.db from the included migrations
python seed.py            # clears tables and adds example exercises and workouts
```

Rerun `python seed.py` at any time to reset the data.

## Running the App

From the `server/` directory:

```bash
flask run --port 5555
```

or

```bash
python app.py
```

The API is served at `http://127.0.0.1:5555`.

## Running the Tests

From the project root:

```bash
pytest
```

The tests use an in-memory SQLite database, so they never touch `app.db`.

## API Endpoints

All requests and responses use JSON. Dates use `YYYY-MM-DD` format.

### Workouts

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/workouts` | List all workouts, newest first. |
| GET | `/workouts/<id>` | Show one workout with its exercises, including reps/sets/duration from each `WorkoutExercise`. |
| POST | `/workouts` | Create a workout. |
| DELETE | `/workouts/<id>` | Delete a workout and its associated `WorkoutExercise` rows. |

**POST /workouts** request body:

```json
{
  "date": "2026-09-21",
  "duration_minutes": 45,
  "notes": "Upper body focus"
}
```

`date` and `duration_minutes` (1-480) are required; `notes` is optional (max 500 characters). Returns `201` with the new workout.

**GET /workouts/1** response:

```json
{
  "id": 1,
  "date": "2026-09-14",
  "duration_minutes": 60,
  "notes": "Lower body strength focus. Client hit a squat PR.",
  "workout_exercises": [
    {
      "id": 1,
      "workout_id": 1,
      "exercise_id": 1,
      "reps": 5,
      "sets": 5,
      "duration_seconds": null,
      "exercise": {
        "id": 1,
        "name": "Back Squat",
        "category": "strength",
        "equipment_needed": true
      }
    }
  ]
}
```

### Exercises

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/exercises` | List all exercises, alphabetically. |
| GET | `/exercises/<id>` | Show one exercise with the workouts it appears in. |
| POST | `/exercises` | Create an exercise. |
| DELETE | `/exercises/<id>` | Delete an exercise and its associated `WorkoutExercise` rows. |

**POST /exercises** request body:

```json
{
  "name": "Burpee",
  "category": "cardio",
  "equipment_needed": false
}
```

`name` (1-100 characters, unique) and `category` are required. `category` must be one of `strength`, `cardio`, `flexibility`, `balance`, or `mobility`. `equipment_needed` defaults to `false`. Returns `201`, or `409` if the name already exists.

### Adding an Exercise to a Workout

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/workouts/<workout_id>/exercises/<exercise_id>/workout_exercises` | Add an exercise to a workout with reps, sets, and/or duration. |

Request body (reps and sets together, a duration, or both):

```json
{ "sets": 3, "reps": 12 }
```

```json
{ "duration_seconds": 60 }
```

All values must be positive integers. Returns `201` with the new entry and its exercise, or `404` if the workout or exercise doesn't exist.

### Status Codes

| Code | Meaning |
| ---- | ------- |
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Validation failed or request body is not JSON |
| 404 | Resource not found |
| 409 | Duplicate exercise name |

Example validation error:

```json
{
  "error": "Validation failed.",
  "details": {
    "date": ["Not a valid date."],
    "duration_minutes": ["Not a valid integer."]
  }
}
```
