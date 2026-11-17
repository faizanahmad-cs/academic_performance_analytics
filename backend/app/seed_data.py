import os
import csv
import json
from datetime import datetime
from sqlalchemy.orm import Session

from .database import engine, SessionLocal, Base
from .models import User, Student, Faculty, Course, AcademicRecord, Attendance, Assignment, Submission, RiskPrediction
from .auth import hash_password
from .ml_engine import risk_engine

CSV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "students_data.csv"))

def clean_val(val, default=0.0):
    try:
        val = str(val).strip()
        return float(val) if val else default
    except Exception:
        return default

def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Check if already seeded
    if db.query(User).filter(User.email == "hod@amu.ac.in").first():
        print("Database already contains seed data.")
        db.close()
        return

    print("Seeding initial HOD, Faculty, Courses and Students...")

    # 1. Create HOD User
    hod_user = User(
        name="Prof. HOD (Computer Science)",
        email="hod@amu.ac.in",
        password_hash=hash_password("hod123"),
        role="HOD",
        created_at=datetime.utcnow()
    )
    db.add(hod_user)

    # 2. Create Faculty Users & Profiles
    faculty_profiles = [
        {"name": "Dr. A. K. Sharma", "email": "faculty.cpp@amu.ac.in"},
        {"name": "Dr. M. Qasim", "email": "faculty.dbms@amu.ac.in"},
        {"name": "Dr. S. Rehan", "email": "faculty.java@amu.ac.in"},
        {"name": "Dr. Farhan Khan", "email": "faculty.web@amu.ac.in"}
    ]
    fac_objects = []
    for fp in faculty_profiles:
        f_user = User(
            name=fp["name"],
            email=fp["email"],
            password_hash=hash_password("faculty123"),
            role="Faculty",
            created_at=datetime.utcnow()
        )
        db.add(f_user)
        db.flush()

        faculty = Faculty(
            user_id=f_user.id,
            name=fp["name"],
            email=fp["email"],
            department="Department of Computer Science"
        )
        db.add(faculty)
        db.flush()
        fac_objects.append(faculty)

    # 3. Create Courses
    course_defs = [
        # Sem 1
        {"code": "CS101", "name": "DS using C++", "sem": 1, "fac_idx": 0},
        {"code": "CS102", "name": "DBMS", "sem": 1, "fac_idx": 1},
        {"code": "CS103", "name": "Digital Electronics", "sem": 1, "fac_idx": 0},
        {"code": "CS104", "name": "Analysis and Design of IS", "sem": 1, "fac_idx": 1},
        {"code": "CS105", "name": "Soft Skills Development", "sem": 1, "fac_idx": 2},
        {"code": "CS106", "name": "Lab-I", "sem": 1, "fac_idx": 0},
        # Sem 2
        {"code": "CS201", "name": "OOPs using JAVA", "sem": 2, "fac_idx": 2},
        {"code": "CS202", "name": "Web Dev", "sem": 2, "fac_idx": 3},
        {"code": "CS203", "name": "Computer Networks", "sem": 2, "fac_idx": 1},
        {"code": "CS204", "name": "Lab-II", "sem": 2, "fac_idx": 2},
        {"code": "CS205", "name": "E-Commerce", "sem": 2, "fac_idx": 3},
        {"code": "CS206", "name": "Open Elective", "sem": 2, "fac_idx": 0},
    ]

    course_map = {}
    for c in course_defs:
        course = Course(
            course_code=c["code"],
            course_name=c["name"],
            semester=c["sem"],
            faculty_id=fac_objects[c["fac_idx"]].id
        )
        db.add(course)
        db.flush()
        course_map[c["name"]] = course

    # 4. Read CSV and populate Students, Academic Records, Attendance, and Predictions
    print(f"Reading student dataset from {CSV_FILE_PATH}...")
    if not os.path.exists(CSV_FILE_PATH):
        print(f"ERROR: CSV file not found at {CSV_FILE_PATH}")
        db.rollback()
        db.close()
        return

    with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        student_count = 0

        for row in reader:
            full_name = row.get("Full Name", "").strip()
            enrollment_no = row.get("Enrollment Number", "").strip()
            section = row.get("Section (leave blank if none)", "").strip()
            username = row.get("Username", "").strip()

            if not full_name or not enrollment_no:
                continue

            student_email = username if username and "@" in username else f"{enrollment_no.lower().replace(' ', '')}@myamu.ac.in"

            # Check if user already exists
            existing_user = db.query(User).filter(User.email == student_email).first()
            if not existing_user:
                s_user = User(
                    name=full_name,
                    email=student_email,
                    password_hash=hash_password("student123"),
                    role="Student",
                    created_at=datetime.utcnow()
                )
                db.add(s_user)
                db.flush()
                user_id = s_user.id
            else:
                user_id = existing_user.id

            student = Student(
                user_id=user_id,
                name=full_name,
                enrollment_no=enrollment_no,
                email=student_email,
                section=section if section else "A"
            )
            db.add(student)
            db.flush()
            student_count += 1

            # Extract marks
            sem1_marks = {
                "DS using C++": clean_val(row.get("Sem 1 - DS using C++ (marks out of 100)")),
                "DBMS": clean_val(row.get("Sem 1 - DBMS (marks out of 100)")),
                "Digital Electronics": clean_val(row.get("Sem 1 - Digital Electronics (marks out of 100)")),
                "Analysis and Design of IS": clean_val(row.get("Sem 1 - Analysis and Design of IS (marks out of 100)")),
                "Soft Skills Development": clean_val(row.get("Sem 1 - Soft Skills Development (marks out of 100)")),
                "Lab-I": clean_val(row.get("Sem 1 - Lab-I (marks out of 100)")),
            }
            sem1_att = clean_val(row.get("Sem 1 - Overall Attendance %"), default=75.0)

            sem2_marks = {
                "OOPs using JAVA": clean_val(row.get("Sem 2 - OOPs using JAVA (marks out of 100)")),
                "Web Dev": clean_val(row.get("Sem 2 - Web Dev (marks out of 100)")),
                "Computer Networks": clean_val(row.get("Sem 2 - Computer Networks (marks out of 100)")),
                "Lab-II": clean_val(row.get("Sem 2 - Lab-II (marks out of 100)")),
                "E-Commerce": clean_val(row.get("Sem 2 - E-Commerce (marks out of 100)")),
                "Open Elective": clean_val(row.get("Sem 2 - Open Elective (marks out of 100)")),
            }
            sem2_att = clean_val(row.get("Sem 2 - Overall Attendance %"), default=75.0)

            # Insert Sem 1 Academic Records
            all_marks = []
            for c_name, mark in sem1_marks.items():
                all_marks.append(mark)
                if c_name in course_map:
                    ar = AcademicRecord(
                        student_id=student.id,
                        course_id=course_map[c_name].id,
                        semester=1,
                        marks=mark
                    )
                    db.add(ar)

            # Insert Sem 2 Academic Records
            for c_name, mark in sem2_marks.items():
                all_marks.append(mark)
                if c_name in course_map:
                    ar = AcademicRecord(
                        student_id=student.id,
                        course_id=course_map[c_name].id,
                        semester=2,
                        marks=mark
                    )
                    db.add(ar)

            # Insert Attendance
            att1 = Attendance(student_id=student.id, semester=1, attendance_percentage=sem1_att)
            att2 = Attendance(student_id=student.id, semester=2, attendance_percentage=sem2_att)
            db.add(att1)
            db.add(att2)

            # Run ML Risk Prediction
            sem1_avg = sum(sem1_marks.values()) / len(sem1_marks) if sem1_marks else 0.0
            sem2_avg = sum(sem2_marks.values()) / len(sem2_marks) if sem2_marks else 0.0
            overall_avg = (sem1_avg + sem2_avg) / 2.0
            overall_att = (sem1_att + sem2_att) / 2.0
            trend = sem2_avg - sem1_avg
            min_mark = min(all_marks) if all_marks else 0.0
            failed_count = sum(1 for m in all_marks if m < 40.0)

            ml_features = {
                "sem1_avg": sem1_avg,
                "sem2_avg": sem2_avg,
                "overall_avg": overall_avg,
                "sem1_attendance": sem1_att,
                "sem2_attendance": sem2_att,
                "overall_attendance": overall_att,
                "trend": trend,
                "min_mark": min_mark,
                "failed_count": failed_count
            }

            pred = risk_engine.predict(ml_features)

            rp = RiskPrediction(
                student_id=student.id,
                risk_level=pred["risk_level"],
                prediction_date=datetime.utcnow(),
                model_result=json.dumps(pred),
                sem1_average=round(sem1_avg, 2),
                sem2_average=round(sem2_avg, 2),
                overall_attendance=round(overall_att, 2)
            )
            db.add(rp)

    # 5. Create Sample Coding Assignments (FR-006)
    assign1 = Assignment(
        faculty_id=fac_objects[0].id,
        course_id=course_map["DS using C++"].id,
        title="Sum of Array Elements",
        problem="Given a space-separated list of integers on standard input, print the sum of all elements.",
        sample_input="1 2 3 4 5",
        sample_output="15",
        test_cases=json.dumps([
            {"input": "1 2 3 4 5", "expected_output": "15"},
            {"input": "10 -5 20", "expected_output": "25"},
            {"input": "100 200 300", "expected_output": "600"}
        ]),
        language="python"
    )
    assign2 = Assignment(
        faculty_id=fac_objects[2].id,
        course_id=course_map["OOPs using JAVA"].id,
        title="Palindrome String Verification",
        problem="Write a program that reads a string and prints 'YES' if it is a palindrome (ignoring case), otherwise 'NO'.",
        sample_input="Radar",
        sample_output="YES",
        test_cases=json.dumps([
            {"input": "Radar", "expected_output": "YES"},
            {"input": "algorithm", "expected_output": "NO"},
            {"input": "level", "expected_output": "YES"}
        ]),
        language="python"
    )
    db.add(assign1)
    db.add(assign2)
    db.flush()

    # 6. Create Sample Submissions for Leaderboard (FR-007, FR-008)
    first_few_students = db.query(Student).limit(8).all()
    sample_scores = [100.0, 100.0, 100.0, 66.7, 100.0, 33.3, 100.0, 66.7]
    for idx, st in enumerate(first_few_students):
        score = sample_scores[idx % len(sample_scores)]
        sub = Submission(
            assignment_id=assign1.id,
            student_id=st.id,
            code="nums = list(map(int, input().split()))\nprint(sum(nums))",
            language="python",
            score=score,
            status="Accepted" if score == 100.0 else "Partially Accepted",
            execution_details=json.dumps({"passed": int(score / 33.3), "total": 3}),
            submitted_at=datetime.utcnow()
        )
        db.add(sub)

    db.commit()
    print(f"Database successfully populated with {student_count} students, marks, attendance, and assignments!")
    db.close()

if __name__ == "__main__":
    seed_database()
