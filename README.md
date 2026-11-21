# Academic Performance Analytics System

### **Department of Computer Science**
### **Aligarh Muslim University, Aligarh – 202002**
**Course:** CAMS-3P01: Mini Project | **M.C.A. Semester – III** (Session: 2026–27)  
**Author:** Faizan Ahmad (Faculty / Enrollment No.: 25CAMSA112)  

---

## 📌 Project Overview
The **Academic Performance Analytics System** is a centralized analytics, early-warning, and automated evaluation platform built strictly to the specifications of the MCA Software Requirements Specification (SRS) document.

It integrates academic mark sheets, attendance percentages (for Semester 1 and Semester 2 from Google Form collection of 60 students), machine-learning risk prediction, and automated programming assignment evaluation using the Judge0 architecture.

---

## 🛠️ Technology Stack (As specified in SRS 2.4 & 4.1)

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend / Presentation** | **Streamlit (Python)** | Interactive role-based dashboard (HOD, Faculty, Student) with Plotly visualization |
| **Backend / REST API** | **FastAPI (Python)** | RESTful API, business logic, CORS, validation |
| **Database** | **SQLite (SQLAlchemy ORM)** | Relational entities, foreign keys, cascade deletes, data integrity |
| **Authentication** | **JWT (python-jose) + bcrypt** | Secure token-based authentication and role-based access control (RBAC) |
| **Machine Learning** | **scikit-learn, Pandas, NumPy** | Random Forest academic risk classification (Low, Medium, High risk) |
| **Online Code Judge** | **Judge0 API + Sandbox Fallback** | Automated programming assignment execution against test cases |
| **Version Control & IDE**| **Git & VS Code** | Development and source tracking |

---

## 📋 SRS Functional Requirements Compliance Matrix

| ID | Requirement | SRS Specification | Status | Implementation Details |
|---|---|---|---|---|
| **FR-001** | **User Authentication & Role-Based Login** | Secure login for HOD, Faculty, and Student users with JWT authentication and bcrypt hashing. | ✅ Complete | Implemented in `backend/app/auth.py` and `/api/v1/auth/login`. |
| **FR-002** | **Student Academic Data Management** | Faculty can add and update student marks for courses they teach. | ✅ Complete | Implemented in `/api/v1/marks` with instant DB update and risk re-calculation. |
| **FR-003** | **Attendance Management** | Faculty can record and update student attendance % per semester. | ✅ Complete | Implemented in `/api/v1/attendance`. |
| **FR-004** | **Student Academic Dashboard** | Students can view their own marks, attendance, coding stats, and predicted risk. | ✅ Complete | Dedicated Student view in Streamlit and `/api/v1/analytics/student-dashboard/{id}`. |
| **FR-005** | **Academic Risk Prediction** | Classify students as Low, Medium, or High risk using marks and attendance trends. | ✅ Complete | Trained `RandomForestClassifier` in `backend/app/ml_engine.py` with intervention notes. |
| **FR-006** | **Coding Assignment Creation** | Faculty can create programming assignments and define test cases. | ✅ Complete | Implemented in `/api/v1/assignments` with JSON test-case storage. |
| **FR-007** | **Automated Code Evaluation** | Evaluate student code through Judge0 API and calculate score out of 100. | ✅ Complete | Implemented in `backend/app/judge0_service.py` with test-case pass/fail breakdown. |
| **FR-008** | **Coding Assignment Leaderboard** | Display coding-assignment scores in a live leaderboard. | ✅ Complete | Implemented in `/api/v1/leaderboard` with rank and problem count. |
| **FR-009** | **HOD Performance Dashboard & Reporting** | Subject-wise average performance reports, risk distribution, and insights. | ✅ Complete | Matches SRS Figure 4.1 Mockup exactly (KPI cards, charts, export). |
| **FR-010** | **Near Real-Time Dashboard Updates** | Reflect new marks/submissions within ~15s without manual reload. | ✅ Complete | 15s refresh triggers and instant state update on submission. |

---

## 📂 Project Directory Structure

```
academic_performance_analytics/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration, JWT secrets, Judge0 API settings
│   │   ├── database.py         # SQLAlchemy SQLite engine and session
│   │   ├── models.py           # 9 Relational Entities (User, Student, Course, etc.)
│   │   ├── schemas.py          # Pydantic data validation schemas
│   │   ├── auth.py             # JWT token handling & bcrypt hashing
│   │   ├── ml_engine.py        # scikit-learn Academic Risk Classifier
│   │   ├── judge0_service.py   # Judge0 automated code evaluation engine
│   │   ├── seed_data.py        # Ingestion script for 60 students from CSV
│   │   └── main.py             # FastAPI REST endpoints
│   └── requirements.txt        # Backend dependencies
├── frontend/
│   ├── app.py                  # Streamlit Interactive Dashboard
│   └── styles.css              # AMU-themed styling (forest green, cards, badges)
├── data/
│   └── students_data.csv       # Original dataset collected via Google Form (60 students)
├── docs/
│   └── SRS.md                  # Complete Software Requirements Specification
├── tests/
│   └── run_tests.py            # Unit test suite verifying all 7 core modules
├── run_system.py               # One-click startup runner for both backend and frontend
└── README.md                   # Project documentation
```

---

## 🚀 How to Run the System

### Option A: One-Click Launch (Recommended)
Run the root launcher which boots both the FastAPI backend and Streamlit dashboard simultaneously:
```bash
python run_system.py
```
- **Streamlit Frontend Dashboard:** [http://localhost:8501](http://localhost:8501)
- **FastAPI Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Option B: Run Services Individually

1. **Start FastAPI Backend:**
   ```bash
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Streamlit Frontend:**
   ```bash
   streamlit run frontend/app.py
   ```

---

## 🔑 Default Demonstration Credentials

| Role | Name | Email / ID | Password | Access / Permissions |
|---|---|---|---|---|
| **HOD** | Prof. HOD (Computer Science) | `hod@amu.ac.in` | `hod123` | Department KPI Cards, Subject Averages, Risk Distribution, Consolidated Reports, Class CSV Export. |
| **Faculty** | Dr. Faisal Anwer | `faisal.anwer@amu.ac.in` | `faculty123` | Add/Update Marks, Update Attendance %, Create Coding Assignments, View Submissions. |
| **Faculty** | Dr. M. Qasim | `faculty.dbms@amu.ac.in` | `faculty123` | DBMS Marks & Attendance management. |
| **Student** | FAIZAN AHMAD | `faizanahmad87635@gmail.com` (or `GR0622`) | `student123` | View Marks (Sem 1 & 2), Attendance %, Risk Prediction, Online Judge Code Submission. |
| **Student** | Any from CSV (Sumit, Adeeba, etc.) | `{enrollment_no}@myamu.ac.in` | `student123` | View individual academic records. |

*(Note: In the Streamlit dashboard sidebar, you can also instantly switch between roles or any of the 60 students using the interactive dropdown!)*

---

## 🧪 Running Automated Tests

Run the comprehensive unit test suite:
```bash
python -m tests.run_tests
```
Expected output:
```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.34s

OK
```
Tests cover:
1. User and student entity population (60 students).
2. Course mapping across Sem 1 and Sem 2 (12 courses).
3. HOD dashboard metrics and aggregation calculations.
4. Student dashboard retrieval and transcript validation.
5. Machine learning risk engine prediction and threshold logic.
6. Code execution and Judge0 test-case verdict evaluation.
7. Leaderboard computation and ranking order.
