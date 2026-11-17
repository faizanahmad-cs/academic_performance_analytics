# DEPARTMENT OF COMPUTER SCIENCE
## ALIGARH MUSLIM UNIVERSITY, ALIGARH-202002
### M.C.A SEMESTER – III | SESSION: 2026-27
### CAMS-3P01: MINI PROJECT
# ACADEMIC PERFORMANCE ANALYTICS SYSTEM
## SOFTWARE REQUIREMENT SPECIFICATION

**SUBMITTED BY:**  
NAME: FAIZAN AHMAD  
FACULTY / ENROLLMENT NO.: 25CAMSA112  

**SUBMITTED TO:**  
[Faculty Name]

---

## Table of Contents
1. Information Gathering Methods
   1.1 Method Comparison
2. Detailed Requirements Specification
   2.1 Functional Requirements
   2.2 Non-Functional Requirements
   2.3 Data Requirements
   2.4 System Requirements
3. Design and Analysis
   3.1 System Architecture
   3.2 Detailed Design Diagram
   3.3 Design Tools and Limitations
4. Implementation
   4.1 Technology Stack Justification
   4.2 Interface Design
   4.3 Implementation Status
5. Preliminary Results and Performance Metrics
6. Scope
7. Feasibility Study
8. Preliminary Development Plan
9. Expected Outcome
10. References

---

## 1. Information Gathering Methods
The requirements for the Academic Performance Analytics System were identified by examining the existing academic-record management process and the proposed centralized method of collecting, storing, and analyzing student academic information. Academic records such as semester marks, attendance, and coding-assignment performance are currently maintained separately and largely manually.

### 1.1 Method Comparison
- **Method 1: Existing Academic Record Analysis**
  - Provides an understanding of how marks, attendance, and coding-assignment records are currently maintained.
  - Helps identify the difficulties faced by the HOD, faculty members, and students.
  - Reveals the need for centralized storage, automated analysis, and early-warning information.
- **Method 2: Structured Google Form-Based Data Collection**
  - Provides a structured mechanism for collecting Semester 1 and Semester 2 academic information.
  - Allows collected information to be imported into the relational database.
  - Reduces the learning curve because the class is already using a Google Form for data collection.

**Most Effective Approach:**  
A combination of existing-process analysis and structured academic-data collection is used. The first establishes the requirements, while the second provides the initial dataset for centralized processing and analytics.

---

## 2. Detailed Requirements Specification

### 2.1 Functional Requirements
| ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-001 | User Authentication and Role-Based Login | Secure login for HOD, Faculty, and Student users with JWT authentication, bcrypt password hashing, and role-based access. | High |
| FR-002 | Student Academic Data Management | Faculty can add and update student marks for courses they teach. | High |
| FR-003 | Attendance Management | Faculty can record student attendance percentage per semester. | High |
| FR-004 | Student Academic Dashboard | Students can view their own marks, attendance, coding performance, and predicted risk. | High |
| FR-005 | Academic Risk Prediction | Classify students as Low, Medium, or High risk using marks and attendance trends. | High |
| FR-006 | Coding Assignment Creation | Faculty can create programming assignments and define test cases. | High |
| FR-007 | Automated Code Evaluation | Evaluate student code through Judge0 API and calculate a score. | High |
| FR-008 | Coding Assignment Leaderboard | Display coding-assignment scores in a live leaderboard. | Medium |
| FR-009 | HOD Performance Dashboard and Reporting | Provide subject-wise average performance reports and consolidated academic insights. | High |
| FR-010 | Near Real-Time Dashboard Updates | Reflect new marks or submissions within approximately 15 seconds without manual reload. | Medium |

### 2.2 Non-Functional Requirements
| Category | Requirement |
|---|---|
| Performance | Dashboard updates should appear within approximately 15 seconds. |
| Security | Only authenticated users can access the system; passwords use bcrypt hashing and endpoints enforce role-based access. |
| Usability | Charts shall be simple and clearly labelled. |
| Reliability | Relational database constraints and foreign keys shall maintain data integrity. |
| Maintainability | Modular and documented components shall support future extension. |

### 2.3 Data Requirements
| Entity | Major Attributes |
|---|---|
| User | User_ID, Name, Email, Password Hash, Role |
| Student | Student_ID, Name, Faculty_No, Enrollment_No, Email |
| Faculty | Faculty_ID, Name, Email, Password Hash |
| Course | Course_ID, Course_Name, Semester, Faculty_ID |
| Academic Record | Record_ID, Student_ID, Course_ID, Semester, Marks |
| Attendance | Attendance_ID, Student_ID, Semester, Attendance_Percentage |
| Coding Assignment | Assignment_ID, Faculty_ID, Course_ID, Title, Problem, Test Cases |
| Code Submission | Submission_ID, Assignment_ID, Student_ID, Code, Score, Status |
| Risk Prediction | Prediction_ID, Student_ID, Risk_Level, Prediction_Date, Model_Result |

*Relationships:* A Student can have many academic and attendance records; Faculty can teach many Courses and create many Assignments; Assignments can receive many Submissions; Students can have multiple Risk Predictions as new academic information is processed.

### 2.4 System Requirements
| Component | Proposed Technology |
|---|---|
| Front-end / Dashboard | Streamlit (Python) |
| Back-end | FastAPI (Python) |
| Database | SQLite; MySQL/PostgreSQL for future scale-up |
| Authentication | JWT tokens with bcrypt password hashing |
| Machine Learning | scikit-learn, Pandas, NumPy |
| Coding Assignment Judge | Judge0 API |
| Development Environment | VS Code |
| Version Control | Git |

---

## 3. Design and Analysis

### 3.1 System Architecture
Layered architecture consisting of:
1. Streamlit presentation layer (HOD Dashboard, Faculty Dashboard, Student Dashboard).
2. FastAPI backend (Authentication, Business Logic, REST API).
3. SQLite Database (Students, Courses, Marks, Attendance, Submissions, Predictions).
4. ML Analytics (Pandas, NumPy, scikit-learn).
5. Judge0 API (Code execution & test cases).

---

## 4. Implementation Details
- **Subject Mappings from Dataset**:
  - **Semester 1**:
    1. Data Structures using C++ (DS using C++)
    2. Database Management Systems (DBMS)
    3. Digital Electronics
    4. Analysis and Design of Information Systems (ADIS)
    5. Soft Skills Development
    6. Lab-I
    7. Overall Attendance %
  - **Semester 2**:
    1. Object-Oriented Programming using JAVA (OOPs using JAVA)
    2. Web Development (Web Dev)
    3. Computer Networks
    4. Lab-II
    5. E-Commerce
    6. Open Elective
    7. Overall Attendance %
