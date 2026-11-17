from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'HOD', 'Faculty', 'Student'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    faculty_profile = relationship("Faculty", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(100), nullable=False)
    faculty_no = Column(String(50), nullable=True)
    enrollment_no = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(150), nullable=True)
    section = Column(String(10), nullable=True)

    # Relationships
    user = relationship("User", back_populates="student_profile")
    academic_records = relationship("AcademicRecord", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    risk_predictions = relationship("RiskPrediction", back_populates="student", cascade="all, delete-orphan")


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    department = Column(String(100), default="Department of Computer Science")

    # Relationships
    user = relationship("User", back_populates="faculty_profile")
    courses = relationship("Course", back_populates="faculty")
    assignments = relationship("Assignment", back_populates="faculty")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), unique=True, index=True, nullable=False)
    course_name = Column(String(150), nullable=False)
    semester = Column(Integer, nullable=False)  # 1 or 2
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)

    # Relationships
    faculty = relationship("Faculty", back_populates="courses")
    academic_records = relationship("AcademicRecord", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")


class AcademicRecord(Base):
    __tablename__ = "academic_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    marks = Column(Float, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="academic_records")
    course = relationship("Course", back_populates="academic_records")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    attendance_percentage = Column(Float, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="attendance_records")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    problem = Column(Text, nullable=False)
    sample_input = Column(Text, nullable=True)
    sample_output = Column(Text, nullable=True)
    test_cases = Column(Text, nullable=False)  # JSON list of dicts: [{"input": "...", "output": "..."}]
    language = Column(String(50), default="python")  # python, cpp, java
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    faculty = relationship("Faculty", back_populates="assignments")
    course = relationship("Course", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    score = Column(Float, default=0.0)
    status = Column(String(50), default="Pending")  # Accepted, Partially Accepted, Wrong Answer, Error
    execution_details = Column(Text, nullable=True)  # JSON results per testcase
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    risk_level = Column(String(50), nullable=False)  # 'Low', 'Medium', 'High'
    prediction_date = Column(DateTime, default=datetime.utcnow)
    model_result = Column(Text, nullable=True)  # JSON metadata, probabilities, reasons
    sem1_average = Column(Float, nullable=True)
    sem2_average = Column(Float, nullable=True)
    overall_attendance = Column(Float, nullable=True)

    # Relationships
    student = relationship("Student", back_populates="risk_predictions")
