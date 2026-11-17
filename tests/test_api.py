import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_login_hod():
    response = client.post("/api/v1/auth/login", json={
        "email": "hod@amu.ac.in",
        "password": "hod123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "HOD"
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_student():
    response = client.post("/api/v1/auth/login", json={
        "email": "faizanahmad87635@gmail.com",
        "password": "student123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "Student"
    assert data["enrollment_no"] == "GR0622"

def test_get_courses():
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) == 12  # 6 courses in Sem 1 + 6 courses in Sem 2

def test_hod_dashboard_metrics():
    response = client.get("/api/v1/analytics/hod-dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_students"] == 60
    assert data["average_marks"] > 0
    assert data["overall_attendance"] > 0
    assert "risk_distribution" in data
    assert len(data["subject_averages"]) == 12

def test_student_dashboard():
    response = client.get("/api/v1/analytics/student-dashboard/1")
    assert response.status_code == 200
    data = response.json()
    assert data["student_info"]["enrollment_no"] == "GR0622"
    assert len(data["sem1_marks"]) == 6
    assert len(data["sem2_marks"]) == 6
    assert data["risk_prediction"] is not None

def test_code_evaluation():
    # Test submission on Assignment 1 (Sum of Array Elements)
    response = client.post("/api/v1/submissions", json={
        "assignment_id": 1,
        "code": "print(sum(map(int, input().split())))",
        "language": "python"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 100.0
    assert data["status"] == "Accepted"

def test_leaderboard():
    response = client.get("/api/v1/leaderboard")
    assert response.status_code == 200
    lb = response.json()
    assert len(lb) > 0
    assert lb[0]["rank"] == 1
