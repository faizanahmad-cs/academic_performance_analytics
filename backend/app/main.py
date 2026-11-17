import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .config import settings
from .database import engine, get_db, Base
from .models import User, Student, Faculty, Course, AcademicRecord, Attendance, Assignment, Submission, RiskPrediction
from .schemas import (
    Token, UserLogin, UserCreate, UserResponse,
    StudentResponse, FacultyResponse, CourseResponse,
    AcademicRecordCreate, AcademicRecordResponse,
    AttendanceCreate, AttendanceResponse,
    AssignmentCreate, AssignmentResponse,
    SubmissionCreate, SubmissionResponse, LeaderboardEntry,
    RiskPredictionResponse, HODDashboardMetrics, StudentDashboardData,
    SubjectAverage, RiskDistribution
)
from .auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from .ml_engine import risk_engine
from .judge0_service import judge_service

# Initialize tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for Academic Performance Analytics System - AMU MCA Mini Project (CAMS-3P01)"
)

# Enable CORS for Streamlit and external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# 1. Authentication Endpoints (FR-001)
# =========================================================================
@app.post(f"{settings.API_V1_STR}/auth/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile_id = None
    enrollment_no = None
    if user.role == "Student" and user.student_profile:
        profile_id = user.student_profile.id
        enrollment_no = user.student_profile.enrollment_no
    elif user.role == "Faculty" and user.faculty_profile:
        profile_id = user.faculty_profile.id

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "user_id": user.id,
        "profile_id": profile_id,
        "enrollment_no": enrollment_no
    }


@app.get(f"{settings.API_V1_STR}/auth/me")
def get_current_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = None
    if current_user.role == "Student" and current_user.student_profile:
        profile = {
            "student_id": current_user.student_profile.id,
            "enrollment_no": current_user.student_profile.enrollment_no,
            "section": current_user.student_profile.section
        }
    elif current_user.role == "Faculty" and current_user.faculty_profile:
        profile = {
            "faculty_id": current_user.faculty_profile.id,
            "department": current_user.faculty_profile.department
        }

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "profile": profile
    }


# =========================================================================
# 2. Student & Course Endpoints
# =========================================================================
@app.get(f"{settings.API_V1_STR}/students", response_model=List[StudentResponse])
def get_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Student).order_by(Student.id).all()


@app.get(f"{settings.API_V1_STR}/students/{{student_id}}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get(f"{settings.API_V1_STR}/courses", response_model=List[CourseResponse])
def get_courses(semester: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Course)
    if semester:
        query = query.filter(Course.semester == semester)
    return query.order_by(Course.semester, Course.id).all()


# =========================================================================
# 3. Academic Data & Attendance Management (FR-002, FR-003)
# =========================================================================
@app.post(f"{settings.API_V1_STR}/marks")
def add_or_update_mark(
    record_in: AcademicRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Faculty", "HOD"]))
):
    existing = db.query(AcademicRecord).filter(
        AcademicRecord.student_id == record_in.student_id,
        AcademicRecord.course_id == record_in.course_id,
        AcademicRecord.semester == record_in.semester
    ).first()

    if existing:
        existing.marks = record_in.marks
    else:
        existing = AcademicRecord(
            student_id=record_in.student_id,
            course_id=record_in.course_id,
            semester=record_in.semester,
            marks=record_in.marks
        )
        db.add(existing)

    db.commit()
    # Trigger risk re-prediction for this student
    _recalculate_student_risk(record_in.student_id, db)
    return {"message": "Marks recorded successfully", "record_id": existing.id}


@app.post(f"{settings.API_V1_STR}/attendance")
def add_or_update_attendance(
    att_in: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Faculty", "HOD"]))
):
    existing = db.query(Attendance).filter(
        Attendance.student_id == att_in.student_id,
        Attendance.semester == att_in.semester
    ).first()

    if existing:
        existing.attendance_percentage = att_in.attendance_percentage
    else:
        existing = Attendance(
            student_id=att_in.student_id,
            semester=att_in.semester,
            attendance_percentage=att_in.attendance_percentage
        )
        db.add(existing)

    db.commit()
    _recalculate_student_risk(att_in.student_id, db)
    return {"message": "Attendance recorded successfully", "attendance_id": existing.id}


# =========================================================================
# 4. Coding Assignments & Evaluation (FR-006, FR-007, FR-008)
# =========================================================================
@app.get(f"{settings.API_V1_STR}/assignments", response_model=List[AssignmentResponse])
def get_assignments(db: Session = Depends(get_db)):
    return db.query(Assignment).order_by(desc(Assignment.created_at)).all()


@app.post(f"{settings.API_V1_STR}/assignments", response_model=AssignmentResponse)
def create_assignment(
    assignment_in: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Faculty", "HOD"]))
):
    faculty = current_user.faculty_profile
    faculty_id = faculty.id if faculty else 1

    assignment = Assignment(
        faculty_id=faculty_id,
        course_id=assignment_in.course_id,
        title=assignment_in.title,
        problem=assignment_in.problem,
        sample_input=assignment_in.sample_input,
        sample_output=assignment_in.sample_output,
        test_cases=json.dumps([tc.model_dump() for tc in assignment_in.test_cases]),
        language=assignment_in.language,
        created_at=datetime.utcnow()
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@app.post(f"{settings.API_V1_STR}/submissions", response_model=SubmissionResponse)
def submit_code(
    submission_in: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Student", "HOD", "Faculty"]))
):
    student = current_user.student_profile
    if not student:
        # Fallback to first student if testing as HOD/Faculty
        student = db.query(Student).first()
        if not student:
            raise HTTPException(status_code=400, detail="No student profile available for submission")

    assignment = db.query(Assignment).filter(Assignment.id == submission_in.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Parse test cases
    try:
        test_cases = json.loads(assignment.test_cases)
    except Exception:
        test_cases = []

    # Evaluate using Judge0 service (or fallback sandbox)
    eval_result = judge_service.evaluate_submission(
        code=submission_in.code,
        language=submission_in.language,
        test_cases=test_cases
    )

    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        code=submission_in.code,
        language=submission_in.language,
        score=eval_result["score"],
        status=eval_result["status"],
        execution_details=json.dumps(eval_result),
        submitted_at=datetime.utcnow()
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "student_id": submission.student_id,
        "student_name": student.name,
        "language": submission.language,
        "score": submission.score,
        "status": submission.status,
        "execution_details": submission.execution_details,
        "submitted_at": submission.submitted_at
    }


@app.get(f"{settings.API_V1_STR}/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    # Group submissions by student, get highest score per assignment
    students = db.query(Student).all()
    leaderboard = []

    for st in students:
        subs = db.query(Submission).filter(Submission.student_id == st.id).all()
        if subs:
            # Get max score per unique assignment
            assign_scores = {}
            for s in subs:
                assign_scores[s.assignment_id] = max(assign_scores.get(s.assignment_id, 0.0), s.score)
            
            total_score = sum(assign_scores.values())
            solved = sum(1 for sc in assign_scores.values() if sc == 100.0)
            
            leaderboard.append({
                "student_id": st.id,
                "student_name": st.name,
                "enrollment_no": st.enrollment_no,
                "total_score": round(total_score, 1),
                "problems_solved": solved
            })

    # Sort descending by total score then problems solved
    leaderboard.sort(key=lambda x: (x["total_score"], x["problems_solved"]), reverse=True)

    result = []
    for rank, entry in enumerate(leaderboard, 1):
        result.append(LeaderboardEntry(rank=rank, **entry))

    return result


# =========================================================================
# 5. HOD Dashboard & Analytics (FR-009, FR-010)
# =========================================================================
@app.get(f"{settings.API_V1_STR}/analytics/hod-dashboard", response_model=HODDashboardMetrics)
def get_hod_dashboard(db: Session = Depends(get_db)):
    total_students = db.query(Student).count()
    if total_students == 0:
        return HODDashboardMetrics(
            total_students=0,
            average_marks=0.0,
            overall_attendance=0.0,
            high_risk_count=0,
            subject_averages=[],
            risk_distribution=RiskDistribution(
                low_risk_count=0, medium_risk_count=0, high_risk_count=0,
                low_risk_pct=0.0, medium_risk_pct=0.0, high_risk_pct=0.0
            ),
            leaderboard=[]
        )

    # Average Marks
    avg_marks = db.query(func.avg(AcademicRecord.marks)).scalar() or 0.0

    # Overall Attendance
    avg_att = db.query(func.avg(Attendance.attendance_percentage)).scalar() or 0.0

    # High Risk Count & Risk Distribution
    risk_preds = db.query(RiskPrediction).all()
    low_cnt = sum(1 for rp in risk_preds if rp.risk_level == "Low")
    med_cnt = sum(1 for rp in risk_preds if rp.risk_level == "Medium")
    high_cnt = sum(1 for rp in risk_preds if rp.risk_level == "High")
    total_preds = max(len(risk_preds), 1)

    risk_dist = RiskDistribution(
        low_risk_count=low_cnt,
        medium_risk_count=med_cnt,
        high_risk_count=high_cnt,
        low_risk_pct=round((low_cnt / total_preds) * 100.0, 1),
        medium_risk_pct=round((med_cnt / total_preds) * 100.0, 1),
        high_risk_pct=round((high_cnt / total_preds) * 100.0, 1)
    )

    # Subject Averages
    courses = db.query(Course).all()
    subject_averages = []
    for c in courses:
        records = db.query(AcademicRecord).filter(AcademicRecord.course_id == c.id).all()
        if records:
            c_marks = [r.marks for r in records]
            avg_m = sum(c_marks) / len(c_marks)
            pass_m = sum(1 for m in c_marks if m >= 40.0) / len(c_marks) * 100.0
        else:
            avg_m = 0.0
            pass_m = 0.0
        
        subject_averages.append(SubjectAverage(
            course_code=c.course_code,
            course_name=c.course_name,
            semester=c.semester,
            average_marks=round(avg_m, 1),
            passing_rate=round(pass_m, 1)
        ))

    leaderboard = get_leaderboard(db)

    return HODDashboardMetrics(
        total_students=total_students,
        average_marks=round(avg_marks, 1),
        overall_attendance=round(avg_att, 1),
        high_risk_count=high_cnt,
        subject_averages=subject_averages,
        risk_distribution=risk_dist,
        leaderboard=leaderboard[:10]  # Top 10 for dashboard
    )


# =========================================================================
# 6. Student Academic Dashboard (FR-004)
# =========================================================================
@app.get(f"{settings.API_V1_STR}/analytics/student-dashboard/{{student_id}}", response_model=StudentDashboardData)
def get_student_dashboard(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Semester 1 & 2 marks
    records = db.query(AcademicRecord).filter(AcademicRecord.student_id == student_id).all()
    sem1_marks = []
    sem2_marks = []
    for r in records:
        item = {
            "course_id": r.course_id,
            "course_code": r.course.course_code,
            "course_name": r.course.course_name,
            "marks": r.marks,
            "status": "Passed" if r.marks >= 40.0 else "Failed"
        }
        if r.semester == 1:
            sem1_marks.append(item)
        else:
            sem2_marks.append(item)

    sem1_avg = sum(m["marks"] for m in sem1_marks) / len(sem1_marks) if sem1_marks else 0.0
    sem2_avg = sum(m["marks"] for m in sem2_marks) / len(sem2_marks) if sem2_marks else 0.0
    all_marks = [m["marks"] for m in sem1_marks + sem2_marks]
    overall_avg = sum(all_marks) / len(all_marks) if all_marks else 0.0

    # Attendance
    att_records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    sem1_att = 0.0
    sem2_att = 0.0
    for a in att_records:
        if a.semester == 1:
            sem1_att = a.attendance_percentage
        elif a.semester == 2:
            sem2_att = a.attendance_percentage
    overall_att = (sem1_att + sem2_att) / 2.0 if (sem1_att or sem2_att) else 0.0

    # Risk Prediction
    risk_pred = db.query(RiskPrediction).filter(RiskPrediction.student_id == student_id).order_by(desc(RiskPrediction.prediction_date)).first()
    risk_response = None
    if risk_pred:
        recs = []
        try:
            mr = json.loads(risk_pred.model_result) if risk_pred.model_result else {}
            recs = mr.get("recommendations", [])
        except Exception:
            pass

        risk_response = RiskPredictionResponse(
            id=risk_pred.id,
            student_id=student.id,
            student_name=student.name,
            enrollment_no=student.enrollment_no,
            risk_level=risk_pred.risk_level,
            prediction_date=risk_pred.prediction_date,
            sem1_average=risk_pred.sem1_average,
            sem2_average=risk_pred.sem2_average,
            overall_attendance=risk_pred.overall_attendance,
            recommendations=recs
        )

    # Submissions
    submissions = db.query(Submission).filter(Submission.student_id == student_id).order_by(desc(Submission.submitted_at)).all()
    sub_responses = [
        SubmissionResponse(
            id=s.id,
            assignment_id=s.assignment_id,
            student_id=s.student_id,
            student_name=student.name,
            language=s.language,
            score=s.score,
            status=s.status,
            execution_details=s.execution_details,
            submitted_at=s.submitted_at
        ) for s in submissions
    ]

    # Leaderboard Rank
    leaderboard = get_leaderboard(db)
    rank = None
    for item in leaderboard:
        if item.student_id == student_id:
            rank = item.rank
            break

    return StudentDashboardData(
        student_info=StudentResponse.model_validate(student),
        sem1_marks=sem1_marks,
        sem2_marks=sem2_marks,
        sem1_avg=round(sem1_avg, 1),
        sem2_avg=round(sem2_avg, 1),
        overall_avg=round(overall_avg, 1),
        sem1_attendance=round(sem1_att, 1),
        sem2_attendance=round(sem2_att, 1),
        overall_attendance=round(overall_att, 1),
        risk_prediction=risk_response,
        coding_submissions=sub_responses,
        leaderboard_rank=rank
    )


# =========================================================================
# Helper Functions
# =========================================================================
def _recalculate_student_risk(student_id: int, db: Session):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return

    records = db.query(AcademicRecord).filter(AcademicRecord.student_id == student_id).all()
    s1_marks = [r.marks for r in records if r.semester == 1]
    s2_marks = [r.marks for r in records if r.semester == 2]
    all_marks = [r.marks for r in records]

    s1_avg = sum(s1_marks) / len(s1_marks) if s1_marks else 0.0
    s2_avg = sum(s2_marks) / len(s2_marks) if s2_marks else 0.0
    overall_avg = sum(all_marks) / len(all_marks) if all_marks else 0.0

    att_records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    s1_att = next((a.attendance_percentage for a in att_records if a.semester == 1), 75.0)
    s2_att = next((a.attendance_percentage for a in att_records if a.semester == 2), 75.0)
    overall_att = (s1_att + s2_att) / 2.0

    features = {
        "sem1_avg": s1_avg,
        "sem2_avg": s2_avg,
        "overall_avg": overall_avg,
        "sem1_attendance": s1_att,
        "sem2_attendance": s2_att,
        "overall_attendance": overall_att,
        "trend": s2_avg - s1_avg,
        "min_mark": min(all_marks) if all_marks else 0.0,
        "failed_count": sum(1 for m in all_marks if m < 40.0)
    }

    pred = risk_engine.predict(features)

    existing_rp = db.query(RiskPrediction).filter(RiskPrediction.student_id == student_id).first()
    if existing_rp:
        existing_rp.risk_level = pred["risk_level"]
        existing_rp.prediction_date = datetime.utcnow()
        existing_rp.model_result = json.dumps(pred)
        existing_rp.sem1_average = round(s1_avg, 2)
        existing_rp.sem2_average = round(s2_avg, 2)
        existing_rp.overall_attendance = round(overall_att, 2)
    else:
        new_rp = RiskPrediction(
            student_id=student_id,
            risk_level=pred["risk_level"],
            prediction_date=datetime.utcnow(),
            model_result=json.dumps(pred),
            sem1_average=round(s1_avg, 2),
            sem2_average=round(s2_avg, 2),
            overall_attendance=round(overall_att, 2)
        )
        db.add(new_rp)

    db.commit()


@app.post(f"{settings.API_V1_STR}/analytics/predict-risk/batch")
def batch_predict_risk(db: Session = Depends(get_db), current_user: User = Depends(require_role(["HOD", "Faculty"]))):
    students = db.query(Student).all()
    updated = 0
    for st in students:
        _recalculate_student_risk(st.id, db)
        updated += 1
    return {"message": f"Successfully updated risk predictions for {updated} students."}
