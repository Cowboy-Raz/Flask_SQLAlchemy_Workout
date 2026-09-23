"""Endpoint behavior, including schema validation errors."""
from models import WorkoutExercise


# ---------- Workouts ----------

def test_get_workouts(client):
    res = client.get("/workouts")
    assert res.status_code == 200
    assert res.get_json()[0]["duration_minutes"] == 60


def test_get_workout_includes_exercises_with_volume(client):
    body = client.get("/workouts/1").get_json()
    entry = body["workout_exercises"][0]
    assert entry["sets"] == 5 and entry["reps"] == 5
    assert entry["exercise"]["name"] == "Back Squat"


def test_get_workout_404(client):
    res = client.get("/workouts/999")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_create_workout(client):
    res = client.post("/workouts", json={"date": "2026-09-20", "duration_minutes": 40})
    assert res.status_code == 201
    assert res.get_json()["date"] == "2026-09-20"


def test_create_workout_schema_errors(client):
    res = client.post("/workouts", json={"date": "not-a-date", "duration_minutes": 0})
    assert res.status_code == 400
    details = res.get_json()["details"]
    assert "date" in details and "duration_minutes" in details


def test_create_workout_rejects_non_json(client):
    res = client.post("/workouts", data="hello")
    assert res.status_code == 400


def test_delete_workout_removes_join_rows(client, app):
    assert client.delete("/workouts/1").status_code == 204
    assert client.get("/workouts/1").status_code == 404
    assert WorkoutExercise.query.count() == 0


# ---------- Exercises ----------

def test_get_exercises(client):
    names = [e["name"] for e in client.get("/exercises").get_json()]
    assert names == ["Back Squat", "Plank"]


def test_get_exercise_includes_workouts(client):
    body = client.get("/exercises/1").get_json()
    assert body["workout_exercises"][0]["workout"]["notes"] == "Leg day"


def test_create_exercise(client):
    res = client.post("/exercises", json={"name": "Burpee", "category": "cardio"})
    assert res.status_code == 201
    assert res.get_json()["equipment_needed"] is False


def test_create_exercise_schema_errors(client):
    res = client.post("/exercises", json={"name": "", "category": "dance"})
    assert res.status_code == 400
    details = res.get_json()["details"]
    assert "name" in details and "category" in details


def test_create_duplicate_exercise(client):
    res = client.post("/exercises", json={"name": "Plank", "category": "balance"})
    assert res.status_code == 409


def test_delete_exercise(client, app):
    assert client.delete("/exercises/1").status_code == 204
    assert WorkoutExercise.query.count() == 0
    assert client.delete("/exercises/1").status_code == 404


# ---------- WorkoutExercises ----------

URL = "/workouts/{}/exercises/{}/workout_exercises"


def test_add_exercise_to_workout_timed(client):
    res = client.post(URL.format(1, 2), json={"duration_seconds": 60})
    assert res.status_code == 201
    body = res.get_json()
    assert body["workout_id"] == 1 and body["exercise"]["name"] == "Plank"


def test_add_exercise_requires_volume(client):
    res = client.post(URL.format(1, 2), json={})
    assert res.status_code == 400


def test_add_exercise_reps_without_sets(client):
    res = client.post(URL.format(1, 2), json={"reps": 10})
    assert res.status_code == 400


def test_add_exercise_rejects_negative(client):
    res = client.post(URL.format(1, 2), json={"sets": 3, "reps": -1})
    assert res.status_code == 400


def test_add_exercise_missing_parents(client):
    assert client.post(URL.format(999, 1), json={"duration_seconds": 30}).status_code == 404
    assert client.post(URL.format(1, 999), json={"duration_seconds": 30}).status_code == 404
