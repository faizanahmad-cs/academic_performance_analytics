from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# ----------------- User & Auth Schemas -----------------
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    user_id: int
    profile_id: Optional[int] = None
    enrollment_no: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserBase(BaseModel):
    name: str
    email: str
    role: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- Student & Faculty Schemas -----------------
class StudentBase(BaseModel):
    name: str
    faculty_no: Optional[str] = None
    enrollment_no: str
    email: Optional[str] = None
    section: Optional[str] = None

class StudentResponse(StudentBase):
    id: int
    user_id: Optional[int] = None

    class Config:
        from_attributes = True

class FacultyBase(BaseModel):
    name: str
    email: str
    department: str

class FacultyResponse(FacultyBase):
    id: int

    class Config:
        from_attributes = True


# ----------------- Course Schemas -----------------
class CourseBase(BaseModel):
    course_code: str
    course_name: str
    semester: int

class CourseResponse(CourseBase):
    id: int
    faculty_id: Optional[int] = None

    class Config:
        from_attributes = True


# ----------------- Academic & Attendance Schemas -----------------
class AcademicRecordBase(BaseModel):
    student_id: int
    course_id: int
    semester: int
    marks: float

class AcademicRecordCreate(AcademicRecordBase):
    pass

class AcademicRecordUpdate(BaseModel):
    marks: float

class AcademicRecordResponse(AcademicRecordBase):
    id: int
    course_name: Optional[str] = None

    class Config:
        from_attributes = True

class AttendanceBase(BaseModel):
    student_id: int
    semester: int
    attendance_percentage: float

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceUpdate(BaseModel):
    attendance_percentage: float

class AttendanceResponse(AttendanceBase):
    id: int

    class Config:
        from_attributes = True


# ----------------- Coding Assignment Schemas -----------------
class TestCase(BaseModel):
    input: str
    expected_output: str

class AssignmentCreate(BaseModel):
    course_id: int
    title: str
    problem: str
    sample_input: Optional[str] = None
    sample_output: Optional[str] = None
    test_cases: List[TestCase]
    language: str = "python"

class AssignmentResponse(BaseModel):
    id: int
    faculty_id: int
    course_id: int
    title: str
    problem: str
    sample_input: Optional[str] = None
    sample_output: Optional[str] = None
    language: str
    created_at: datetime

    class Config:
        from_attributes = True

class SubmissionCreate(BaseModel):
    assignment_id: int
    code: str
    language: str = "python"

class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    assignment_title: Optional[str] = None
    student_id: int
    student_name: Optional[str] = None
    code: Optional[str] = None
    language: str
    score: float
    status: str
    execution_details: Optional[str] = None
    submitted_at: datetime

    class Config:
        from_attributes = True

class LeaderboardEntry(BaseModel):
    rank: int
    student_id: int
    student_name: str
    enrollment_no: str
    total_score: float
    problems_solved: int


# ----------------- Risk Prediction & Analytics Schemas -----------------
class RiskPredictionResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    enrollment_no: Optional[str] = None
    risk_level: str
    prediction_date: datetime
    sem1_average: Optional[float] = None
    sem2_average: Optional[float] = None
    overall_attendance: Optional[float] = None
    recommendations: Optional[List[str]] = None

    class Config:
        from_attributes = True

class SubjectAverage(BaseModel):
    course_code: str
    course_name: str
    semester: int
    average_marks: float
    passing_rate: float

class RiskDistribution(BaseModel):
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    low_risk_pct: float
    medium_risk_pct: float
    high_risk_pct: float

class HODDashboardMetrics(BaseModel):
    total_students: int
    average_marks: float
    overall_attendance: float
    high_risk_count: int
    subject_averages: List[SubjectAverage]
    risk_distribution: RiskDistribution
    leaderboard: List[LeaderboardEntry]

class StudentDashboardData(BaseModel):
    student_info: StudentResponse
    sem1_marks: List[Dict[str, Any]]
    sem2_marks: List[Dict[str, Any]]
    sem1_avg: float
    sem2_avg: float
    overall_avg: float
    sem1_attendance: float
    sem2_attendance: float
    overall_attendance: float
    risk_prediction: Optional[RiskPredictionResponse] = None
    coding_submissions: List[SubmissionResponse]
    leaderboard_rank: Optional[int] = None
