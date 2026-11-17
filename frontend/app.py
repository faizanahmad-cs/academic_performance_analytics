import os
import sys
import json
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure page
st.set_page_config(
    page_title="Academic Performance Analytics | AMU",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

# Apply custom styling
CSS_PATH = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# -------------------------------------------------------------
# Session State Management
# -------------------------------------------------------------
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = "HOD"  # Default view
if "user_name" not in st.session_state:
    st.session_state.user_name = "Prof. HOD (Computer Science)"
if "user_id" not in st.session_state:
    st.session_state.user_id = 1
if "profile_id" not in st.session_state:
    st.session_state.profile_id = 1
if "enrollment_no" not in st.session_state:
    st.session_state.enrollment_no = "GR0622"

def api_get(endpoint, params=None):
    headers = {"Authorization": f"Bearer {st.session_state.auth_token}"} if st.session_state.auth_token else {}
    endpoint_clean = endpoint.lstrip('/')
    try:
        res = requests.get(f"{API_URL}/{endpoint_clean}", headers=headers, params=params, timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass

    # Direct database fallback for standalone UI launch
    try:
        from backend.app.database import SessionLocal
        from backend.app.models import Student, Course, Assignment, Submission
        from backend.app.main import get_hod_dashboard, get_student_dashboard, get_leaderboard
        
        db = SessionLocal()
        try:
            if "analytics/hod-dashboard" in endpoint_clean:
                return get_hod_dashboard(db).model_dump()
            elif "analytics/student-dashboard" in endpoint_clean:
                st_id = int(endpoint_clean.split('/')[-1])
                return get_student_dashboard(st_id, db).model_dump()
            elif endpoint_clean == "students":
                st_list = db.query(Student).all()
                return [{"id": s.id, "name": s.name, "enrollment_no": s.enrollment_no, "section": s.section, "email": s.email} for s in st_list]
            elif endpoint_clean == "courses":
                c_list = db.query(Course).all()
                return [{"id": c.id, "course_code": c.course_code, "course_name": c.course_name, "semester": c.semester} for c in c_list]
            elif endpoint_clean == "leaderboard":
                lb = get_leaderboard(db)
                return [l.model_dump() for l in lb]
            elif endpoint_clean == "assignments":
                assigns = db.query(Assignment).all()
                return [{"id": a.id, "title": a.title, "problem": a.problem, "sample_input": a.sample_input, "sample_output": a.sample_output, "language": a.language} for a in assigns]
        finally:
            db.close()
    except Exception as e:
        pass

    return None

def api_post(endpoint, json_data):
    headers = {"Authorization": f"Bearer {st.session_state.auth_token}"} if st.session_state.auth_token else {}
    endpoint_clean = endpoint.lstrip('/')
    try:
        res = requests.post(f"{API_URL}/{endpoint_clean}", headers=headers, json=json_data, timeout=5)
        if res.status_code in [200, 201]:
            return res
    except Exception:
        pass

    # Direct database fallback for operations
    try:
        from backend.app.database import SessionLocal
        from backend.app.models import AcademicRecord, Attendance, Assignment, Submission, Student
        from backend.app.main import _recalculate_student_risk
        from backend.app.judge0_service import judge_service
        from datetime import datetime

        db = SessionLocal()
        try:
            if endpoint_clean == "marks":
                st_id = json_data["student_id"]
                c_id = json_data["course_id"]
                sem = json_data["semester"]
                marks = json_data["marks"]
                rec = db.query(AcademicRecord).filter(
                    AcademicRecord.student_id == st_id,
                    AcademicRecord.course_id == c_id,
                    AcademicRecord.semester == sem
                ).first()
                if rec:
                    rec.marks = marks
                else:
                    rec = AcademicRecord(student_id=st_id, course_id=c_id, semester=sem, marks=marks)
                    db.add(rec)
                db.commit()
                _recalculate_student_risk(st_id, db)
                class MockRes:
                    status_code = 200
                    def json(self): return {"message": "Success"}
                return MockRes()

            elif endpoint_clean == "attendance":
                st_id = json_data["student_id"]
                sem = json_data["semester"]
                att_val = json_data["attendance_percentage"]
                att = db.query(Attendance).filter(
                    Attendance.student_id == st_id,
                    Attendance.semester == sem
                ).first()
                if att:
                    att.attendance_percentage = att_val
                else:
                    att = Attendance(student_id=st_id, semester=sem, attendance_percentage=att_val)
                    db.add(att)
                db.commit()
                _recalculate_student_risk(st_id, db)
                class MockRes:
                    status_code = 200
                    def json(self): return {"message": "Success"}
                return MockRes()

            elif endpoint_clean == "submissions":
                assign_id = json_data["assignment_id"]
                code = json_data["code"]
                lang = json_data.get("language", "python")
                assign = db.query(Assignment).filter(Assignment.id == assign_id).first()
                test_cases = json.loads(assign.test_cases) if assign and assign.test_cases else []
                eval_res = judge_service.evaluate_submission(code, lang, test_cases)
                first_st = db.query(Student).first()
                sub = Submission(
                    assignment_id=assign_id,
                    student_id=first_st.id if first_st else 1,
                    code=code,
                    language=lang,
                    score=eval_res["score"],
                    status=eval_res["status"],
                    execution_details=json.dumps(eval_res),
                    submitted_at=datetime.utcnow()
                )
                db.add(sub)
                db.commit()
                class MockRes:
                    status_code = 200
                    def json(self):
                        return {
                            "score": eval_res["score"],
                            "status": eval_res["status"],
                            "execution_details": json.dumps(eval_res)
                        }
                return MockRes()
        finally:
            db.close()
    except Exception as e:
        pass

    return None

# -------------------------------------------------------------
# Top Banner / Header
# -------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1>Department of Computer Science</h1>
            <p><strong>Aligarh Muslim University, Aligarh</strong> | M.C.A. Session 2026-27 (CAMS-3P01)</p>
            <p style="font-size: 13px; color: #b7e4c7; margin-top: 4px;">Academic Performance Analytics System &bull; Faizan Ahmad (25CAMSA112)</p>
        </div>
        <div style="text-align:right;">
            <span style="background: rgba(255,255,255,0.2); padding: 6px 14px; border-radius: 20px; font-weight:600; font-size:13px;">
                🟢 System Active (Near Real-Time)
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Sidebar Navigation & Role Authentication
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔐 User Portal")
    role_choice = st.selectbox(
        "Current Active Role:",
        ["HOD (Head of Department)", "Faculty Member", "Student"],
        index=0 if st.session_state.user_role == "HOD" else (1 if st.session_state.user_role == "Faculty" else 2)
    )

    if "HOD" in role_choice:
        st.session_state.user_role = "HOD"
        st.session_state.user_name = "Prof. HOD (Computer Science)"
        st.session_state.user_id = 1
    elif "Faculty" in role_choice:
        st.session_state.user_role = "Faculty"
        st.session_state.user_name = "Dr. A. K. Sharma"
        st.session_state.user_id = 2
        st.session_state.profile_id = 1
    else:
        st.session_state.user_role = "Student"
        # Let user choose a student for quick inspection
        st.session_state.user_name = "FAIZAN AHMAD"
        st.session_state.enrollment_no = "GR0622"
        st.session_state.profile_id = 1

    st.markdown(f"**Logged in as:** `{st.session_state.user_name}`")
    st.markdown(f"**Role:** `{st.session_state.user_role}`")
    st.markdown("---")

    # Navigation per role
    if st.session_state.user_role == "HOD":
        menu = st.radio("Navigation", [
            "📊 Executive Dashboard",
            "👥 Student Records & Search",
            "📈 Correlation & Trends",
            "📄 Export Reports"
        ])
    elif st.session_state.user_role == "Faculty":
        menu = st.radio("Navigation", [
            "📝 Manage Marks & Attendance",
            "💻 Create Coding Assignment",
            "📥 View Student Submissions",
            "🏆 Coding Leaderboard"
        ])
    else:  # Student
        menu = st.radio("Navigation", [
            "🎓 My Academic Dashboard",
            "⚠️ AI Risk & Mentoring",
            "💻 Coding Practice Lab",
            "🏆 Live Leaderboard"
        ])

    st.markdown("---")
    st.caption("AMU MCA Mini Project &bull; Streamlit + FastAPI + SQLite + scikit-learn + Judge0")


# -------------------------------------------------------------
# Role 1: HOD View
# -------------------------------------------------------------
if st.session_state.user_role == "HOD":
    # Fetch data
    hod_data = api_get("analytics/hod-dashboard")

    if menu == "📊 Executive Dashboard":
        st.markdown("## 📊 Head of Department (HOD) Performance Overview")
        st.write("Consolidated departmental performance, attendance analytics, and early risk identification.")

        # Real-time refresh button (FR-010)
        c_btn, _ = st.columns([2, 8])
        with c_btn:
            if st.button("🔄 Refresh Data (15s Real-Time Sync)"):
                st.rerun()

        if hod_data:
            # 1. KPI Cards (Matches SRS Mockup Figure 4.1)
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">Total Students</div>
                    <div class="kpi-value">{hod_data.get('total_students', 60)}</div>
                </div>
                """, unsafe_allow_html=True)
            with k2:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">Average Marks</div>
                    <div class="kpi-value">{hod_data.get('average_marks', 74.0)}%</div>
                </div>
                """, unsafe_allow_html=True)
            with k3:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">Average Attendance</div>
                    <div class="kpi-value">{hod_data.get('overall_attendance', 82.0)}%</div>
                </div>
                """, unsafe_allow_html=True)
            with k4:
                high_risk = hod_data.get('high_risk_count', 8)
                st.markdown(f"""
                <div class="kpi-card" style="border-left: 5px solid #dc3545;">
                    <div class="kpi-title">High Risk Students</div>
                    <div class="kpi-value" style="color: #dc3545;">{high_risk}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 2. Charts (Matches Figure 4.1: Subject-wise Performance + Academic Risk Distribution)
            col_chart1, col_chart2 = st.columns([3, 2])

            with col_chart1:
                st.markdown("### 📚 Subject-wise Average Performance")
                subj_list = hod_data.get("subject_averages", [])
                if subj_list:
                    df_subj = pd.DataFrame(subj_list)
                    fig_subj = px.bar(
                        df_subj,
                        x="course_name",
                        y="average_marks",
                        color="semester",
                        title="Average Marks by Course (Sem 1 & Sem 2)",
                        labels={"average_marks": "Average Marks (100)", "course_name": "Course", "semester": "Semester"},
                        text="average_marks",
                        color_discrete_sequence=["#0b5e36", "#2a9d8f"]
                    )
                    fig_subj.update_layout(xaxis_tickangle=-35, margin=dict(b=80))
                    st.plotly_chart(fig_subj, use_container_width=True)
                else:
                    st.info("No subject averages available.")

            with col_chart2:
                st.markdown("### ⚠️ Academic Risk Distribution")
                risk_dist = hod_data.get("risk_distribution", {})
                labels = ["Low Risk", "Medium Risk", "High Risk"]
                values = [
                    risk_dist.get("low_risk_count", 38),
                    risk_dist.get("medium_risk_count", 14),
                    risk_dist.get("high_risk_count", 8)
                ]
                colors = ["#28a745", "#ffc107", "#dc3545"]
                fig_risk = px.pie(
                    names=labels,
                    values=values,
                    color=labels,
                    color_discrete_map={"Low Risk": "#28a745", "Medium Risk": "#ffc107", "High Risk": "#dc3545"},
                    hole=0.4
                )
                fig_risk.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_risk, use_container_width=True)

            st.markdown("---")

            # 3. Coding Assignment Leaderboard (Matches Figure 4.1 bottom)
            st.markdown("### 🏆 Coding Assignment Leaderboard")
            leaderboard_data = hod_data.get("leaderboard", [])
            if leaderboard_data:
                df_lb = pd.DataFrame(leaderboard_data)
                st.dataframe(
                    df_lb[["rank", "student_name", "enrollment_no", "total_score", "problems_solved"]],
                    column_config={
                        "rank": "Rank #",
                        "student_name": "Student Name",
                        "enrollment_no": "Enrollment No.",
                        "total_score": "Score (pts)",
                        "problems_solved": "Problems Solved"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Leaderboard data currently empty.")

        else:
            st.warning("⚠️ FastAPI Backend is offline or initializing. Please launch backend with `python -m uvicorn backend.app.main:app --reload`.")

    elif menu == "👥 Student Records & Search":
        st.markdown("## 👥 Student Records & Detailed Transcript")
        students = api_get("students")
        if students:
            df_st = pd.DataFrame(students)
            
            c_srch, c_sec = st.columns([3, 1])
            with c_srch:
                search_q = st.text_input("🔍 Search Student by Name or Enrollment Number:")
            with c_sec:
                sections = ["All"] + list(df_st["section"].dropna().unique()) if "section" in df_st else ["All"]
                sec_filter = st.selectbox("Filter Section:", sections)

            if search_q:
                df_st = df_st[
                    df_st["name"].str.contains(search_q, case=False, na=False) |
                    df_st["enrollment_no"].str.contains(search_q, case=False, na=False)
                ]
            if sec_filter != "All":
                df_st = df_st[df_st["section"] == sec_filter]

            st.dataframe(df_st[["id", "name", "enrollment_no", "section", "email"]], use_container_width=True, hide_index=True)

            # Drill down into individual student
            st.markdown("### 🔎 Inspect Individual Student Profile")
            st_ids = df_st["id"].tolist()
            if st_ids:
                selected_id = st.selectbox("Select Student:", st_ids, format_func=lambda x: f"{df_st[df_st['id']==x]['name'].values[0]} ({df_st[df_st['id']==x]['enrollment_no'].values[0]})")
                st_detail = api_get(f"analytics/student-dashboard/{selected_id}")
                if st_detail:
                    st.success(f"**Student:** {st_detail['student_info']['name']} | **Enrollment:** {st_detail['student_info']['enrollment_no']} | **Overall Average:** {st_detail['overall_avg']}% | **Attendance:** {st_detail['overall_attendance']}%")
                    
                    rp = st_detail.get("risk_prediction")
                    if rp:
                        risk_level = rp.get("risk_level", "Low")
                        badge_class = f"risk-badge-{risk_level.lower()}"
                        st.markdown(f"**Risk Level:** <span class='{badge_class}'>{risk_level} Risk</span>", unsafe_allow_html=True)
                        if rp.get("recommendations"):
                            st.markdown("**Mentoring Notes:**")
                            for rec in rp["recommendations"]:
                                st.markdown(f"- {rec}")

    elif menu == "📈 Correlation & Trends":
        st.markdown("## 📈 Attendance vs Performance Correlation Analytics")
        students = api_get("students")
        if students:
            # Gather attendance and avg marks for all students
            records_data = []
            for s in students:
                s_info = api_get(f"analytics/student-dashboard/{s['id']}")
                if s_info:
                    records_data.append({
                        "Name": s["name"],
                        "Enrollment": s["enrollment_no"],
                        "Attendance": s_info["overall_attendance"],
                        "Average_Marks": s_info["overall_avg"],
                        "Risk": s_info.get("risk_prediction", {}).get("risk_level", "Low") if s_info.get("risk_prediction") else "Low"
                    })
            
            if records_data:
                df_corr = pd.DataFrame(records_data)
                fig_scatter = px.scatter(
                    df_corr,
                    x="Attendance",
                    y="Average_Marks",
                    color="Risk",
                    hover_name="Name",
                    title="Attendance % vs Average Academic Marks (Correlation Analysis)",
                    labels={"Attendance": "Attendance Percentage (%)", "Average_Marks": "Average Marks (%)"},
                    color_discrete_map={"Low": "#28a745", "Medium": "#ffc107", "High": "#dc3545"},
                    trendline="ols"
                )
                # Add mandatory 75% attendance threshold line
                fig_scatter.add_vline(x=75, line_dash="dash", line_color="red", annotation_text="AMU 75% Rule")
                st.plotly_chart(fig_scatter, use_container_width=True)

    elif menu == "📄 Export Reports":
        st.markdown("## 📄 Academic Performance Report Generation")
        st.write("Generate and download class-wide performance statements for Departmental academic records.")
        students = api_get("students")
        if students:
            export_rows = []
            for s in students:
                s_info = api_get(f"analytics/student-dashboard/{s['id']}")
                if s_info:
                    export_rows.append({
                        "Enrollment No": s["enrollment_no"],
                        "Student Name": s["name"],
                        "Section": s["section"],
                        "Sem 1 Avg": s_info["sem1_avg"],
                        "Sem 2 Avg": s_info["sem2_avg"],
                        "Overall Avg": s_info["overall_avg"],
                        "Overall Attendance %": s_info["overall_attendance"],
                        "Risk Classification": s_info.get("risk_prediction", {}).get("risk_level", "N/A") if s_info.get("risk_prediction") else "N/A"
                    })
            df_exp = pd.DataFrame(export_rows)
            st.dataframe(df_exp, use_container_width=True)

            csv_file = df_exp.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Consolidated Class Report (CSV)",
                data=csv_file,
                file_name="AMU_MCA_Academic_Performance_Report.csv",
                mime="text/csv"
            )


# -------------------------------------------------------------
# Role 2: Faculty View (FR-002, FR-003, FR-006)
# -------------------------------------------------------------
elif st.session_state.user_role == "Faculty":
    st.markdown("## 👨‍🏫 Faculty Academic Management Portal")
    st.write(f"Logged in as **{st.session_state.user_name}** | Department of Computer Science")

    courses = api_get("courses") or []
    students = api_get("students") or []

    if menu == "📝 Manage Marks & Attendance":
        t1, t2 = st.tabs(["📝 Add / Update Student Marks (FR-002)", "📅 Add / Update Attendance (FR-003)"])

        with t1:
            st.markdown("### Update Student Course Marks")
            if courses and students:
                col_c, col_sem = st.columns(2)
                with col_c:
                    course_names = {c["id"]: f"{c['course_code']} - {c['course_name']} (Sem {c['semester']})" for c in courses}
                    selected_c_id = st.selectbox("Select Course:", list(course_names.keys()), format_func=lambda x: course_names[x])
                with col_sem:
                    selected_course = next(c for c in courses if c["id"] == selected_c_id)
                    sem_val = selected_course["semester"]
                    st.info(f"Semester: **{sem_val}**")

                col_s, col_m = st.columns([3, 1])
                with col_s:
                    st_map = {s["id"]: f"{s['name']} ({s['enrollment_no']})" for s in students}
                    selected_st_id = st.selectbox("Select Student:", list(st_map.keys()), format_func=lambda x: st_map[x])
                with col_m:
                    marks_val = st.number_input("Marks (out of 100):", min_value=0.0, max_value=100.0, value=75.0, step=1.0)

                if st.button("💾 Save & Recalculate Risk"):
                    res = api_post("marks", {
                        "student_id": selected_st_id,
                        "course_id": selected_c_id,
                        "semester": sem_val,
                        "marks": marks_val
                    })
                    if res and res.status_code == 200:
                        st.success("Marks saved successfully! Machine learning risk model re-evaluated for student.")
                    else:
                        st.error("Failed to save marks. Check connection.")

        with t2:
            st.markdown("### Update Semester Attendance Percentage")
            if students:
                c_st, c_sem, c_att = st.columns([3, 1, 1])
                with c_st:
                    att_st_id = st.selectbox("Student:", list(st_map.keys()), format_func=lambda x: st_map[x], key="att_st")
                with c_sem:
                    att_sem = st.selectbox("Semester:", [1, 2])
                with c_att:
                    att_val = st.number_input("Attendance %:", min_value=0.0, max_value=100.0, value=80.0, step=0.5)

                if st.button("💾 Save Attendance"):
                    res = api_post("attendance", {
                        "student_id": att_st_id,
                        "semester": att_sem,
                        "attendance_percentage": att_val
                    })
                    if res and res.status_code == 200:
                        st.success("Attendance updated successfully!")
                    else:
                        st.error("Failed to update attendance.")

    elif menu == "💻 Create Coding Assignment":
        st.markdown("### 💻 Create New Programming Assignment (FR-006)")
        st.write("Set problem statement, test cases, and language constraints for automated code evaluation.")

        if courses:
            c_course = st.selectbox("Associated Course:", [c["id"] for c in courses], format_func=lambda x: next(c["course_name"] for c in courses if c["id"] == x))
            assign_title = st.text_input("Assignment Title:", "Find Maximum in Array")
            assign_desc = st.text_area("Problem Statement:", "Read space-separated integers from stdin and output the maximum number.")
            
            c_sin, c_sout = st.columns(2)
            with c_sin:
                sample_in = st.text_area("Sample Input:", "10 45 2 99 3")
            with c_sout:
                sample_out = st.text_area("Sample Output:", "99")

            st.markdown("#### Test Cases for Automated Judge0 Evaluation")
            tc_in_1 = st.text_input("Test Case 1 Input:", "1 2 3 4 5")
            tc_out_1 = st.text_input("Test Case 1 Expected Output:", "5")
            tc_in_2 = st.text_input("Test Case 2 Input:", "-10 -20 -5 -30")
            tc_out_2 = st.text_input("Test Case 2 Expected Output:", "-5")

            if st.button("🚀 Publish Assignment"):
                test_cases = [
                    {"input": tc_in_1, "expected_output": tc_out_1},
                    {"input": tc_in_2, "expected_output": tc_out_2}
                ]
                res = api_post("assignments", {
                    "course_id": c_course,
                    "title": assign_title,
                    "problem": assign_desc,
                    "sample_input": sample_in,
                    "sample_output": sample_out,
                    "test_cases": test_cases,
                    "language": "python"
                })
                if res and res.status_code == 200:
                    st.success("Assignment created successfully and made available to students!")
                else:
                    st.error("Failed to create assignment.")

    elif menu == "📥 View Student Submissions":
        st.markdown("## 📥 Student Coding Submissions")
        # Submissions view
        assigns = api_get("assignments") or []
        if assigns:
            assign_choice = st.selectbox("Select Assignment:", [a["id"] for a in assigns], format_func=lambda x: next(a["title"] for a in assigns if a["id"] == x))
            subs = api_get("submissions", params={"assignment_id": assign_choice}) or []
            if subs:
                df_subs = pd.DataFrame(subs)
                st.dataframe(df_subs[["id", "student_name", "score", "status", "language", "submitted_at"]], use_container_width=True)
            else:
                st.info("No submissions yet for this assignment.")

    elif menu == "🏆 Coding Leaderboard":
        st.markdown("## 🏆 Live Departmental Coding Leaderboard")
        lb = api_get("leaderboard") or []
        if lb:
            df_lb = pd.DataFrame(lb)
            st.dataframe(df_lb[["rank", "student_name", "enrollment_no", "total_score", "problems_solved"]], use_container_width=True)


# -------------------------------------------------------------
# Role 3: Student View (FR-004, FR-005, FR-007)
# -------------------------------------------------------------
else:
    st.markdown("## 🎓 Student Academic Dashboard")
    students = api_get("students") or []
    
    # Allow choosing which student record to view
    if students:
        selected_st_obj = next((s for s in students if s["enrollment_no"] == st.session_state.enrollment_no), students[0])
        col_sel, _ = st.columns([3, 5])
        with col_sel:
            st_choice = st.selectbox(
                "Switch Student Profile:",
                [s["id"] for s in students],
                index=[s["id"] for s in students].index(selected_st_obj["id"]),
                format_func=lambda x: f"{next(s['name'] for s in students if s['id']==x)} ({next(s['enrollment_no'] for s in students if s['id']==x)})"
            )
        st_data = api_get(f"analytics/student-dashboard/{st_choice}")
    else:
        st_data = None

    if st_data:
        st_info = st_data["student_info"]

        if menu == "🎓 My Academic Dashboard":
            st.markdown(f"""
            <div style="background:#e8f5e9; padding:16px 20px; border-radius:10px; margin-bottom:20px; border-left:5px solid #0b5e36;">
                <h3 style="margin:0; color:#0b5e36;">{st_info['name']}</h3>
                <p style="margin:4px 0 0 0; color:#2e7d32;">
                    <strong>Enrollment No:</strong> {st_info['enrollment_no']} | 
                    <strong>Section:</strong> {st_info.get('section', 'A')} | 
                    <strong>Email:</strong> {st_info.get('email', 'N/A')}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Overview metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Sem 1 Average", f"{st_data['sem1_avg']}%")
            with m2:
                st.metric("Sem 2 Average", f"{st_data['sem2_avg']}%")
            with m3:
                st.metric("Overall Percentage", f"{st_data['overall_avg']}%")
            with m4:
                att = st_data["overall_attendance"]
                st.metric("Overall Attendance", f"{att}%", delta="Eligible (>=75%)" if att >= 75 else "At Risk (<75%)", delta_color="normal" if att >= 75 else "inverse")

            st.markdown("### 📋 Subject-wise Marks Breakdown")
            c_sem1, c_sem2 = st.columns(2)

            with c_sem1:
                st.markdown("#### Semester 1 Courses")
                df_s1 = pd.DataFrame(st_data["sem1_marks"])
                if not df_s1.empty:
                    fig_s1 = px.bar(df_s1, x="course_name", y="marks", color="marks", color_continuous_scale="greens", text="marks")
                    fig_s1.update_layout(xaxis_tickangle=-30, yaxis_range=[0, 100])
                    st.plotly_chart(fig_s1, use_container_width=True)
                    st.dataframe(df_s1[["course_code", "course_name", "marks", "status"]], hide_index=True, use_container_width=True)

            with c_sem2:
                st.markdown("#### Semester 2 Courses")
                df_s2 = pd.DataFrame(st_data["sem2_marks"])
                if not df_s2.empty:
                    fig_s2 = px.bar(df_s2, x="course_name", y="marks", color="marks", color_continuous_scale="teal", text="marks")
                    fig_s2.update_layout(xaxis_tickangle=-30, yaxis_range=[0, 100])
                    st.plotly_chart(fig_s2, use_container_width=True)
                    st.dataframe(df_s2[["course_code", "course_name", "marks", "status"]], hide_index=True, use_container_width=True)

        elif menu == "⚠️ AI Risk & Mentoring":
            st.markdown("## 🤖 Machine Learning Academic Risk Classification (FR-005)")
            st.write("Trained Random Forest Classifier evaluating marks, attendance, and trend trajectories.")

            rp = st_data.get("risk_prediction")
            if rp:
                risk_lvl = rp.get("risk_level", "Low")
                if risk_lvl == "Low":
                    st.success("### ✅ Risk Category: LOW RISK")
                    st.write("You are maintaining solid academic momentum and healthy attendance.")
                elif risk_lvl == "Medium":
                    st.warning("### ⚠️ Risk Category: MEDIUM RISK")
                    st.write("You are on track but need caution in select subjects or attendance regularity.")
                else:
                    st.error("### 🚨 Risk Category: HIGH RISK")
                    st.write("Urgent intervention needed. Your marks or attendance require immediate improvement.")

                st.markdown("#### 💡 Actionable Mentoring Recommendations:")
                for rec in rp.get("recommendations", []):
                    st.markdown(f"- 📌 {rec}")
            else:
                st.info("No risk prediction available yet.")

        elif menu == "💻 Coding Practice Lab":
            st.markdown("## 💻 Online Coding Lab & Automated Evaluation (FR-007)")
            st.write("Submit code to be judged against automated test cases through Judge0.")

            assigns = api_get("assignments") or []
            if assigns:
                sel_assign_id = st.selectbox("Select Problem:", [a["id"] for a in assigns], format_func=lambda x: next(a["title"] for a in assigns if a["id"] == x))
                curr_assign = next(a for a in assigns if a["id"] == sel_assign_id)

                st.markdown(f"### {curr_assign['title']}")
                st.info(curr_assign["problem"])

                if curr_assign.get("sample_input"):
                    c_in, c_out = st.columns(2)
                    with c_in:
                        st.markdown("**Sample Input:**")
                        st.code(curr_assign["sample_input"])
                    with c_out:
                        st.markdown("**Sample Output:**")
                        st.code(curr_assign["sample_output"])

                user_code = st.text_area(
                    "Write your Python solution below:",
                    value="# Write solution here\nimport sys\n\nline = sys.stdin.read().strip()\nif line:\n    print(sum(map(int, line.split())))\n",
                    height=200
                )

                if st.button("🚀 Submit to Judge0 Engine"):
                    with st.spinner("Submitting and running automated test cases..."):
                        sub_res = api_post("submissions", {
                            "assignment_id": sel_assign_id,
                            "code": user_code,
                            "language": "python"
                        })
                        if sub_res and sub_res.status_code == 200:
                            sub_data = sub_res.json()
                            score = sub_data.get("score", 0.0)
                            status_text = sub_data.get("status", "Pending")

                            if score == 100.0:
                                st.success(f"🎉 **Verdict: {status_text} | Score: {score}/100**")
                            elif score > 0:
                                st.warning(f"⚠️ **Verdict: {status_text} | Score: {score}/100**")
                            else:
                                st.error(f"❌ **Verdict: {status_text} | Score: {score}/100**")

                            # Show testcase details
                            exec_details = sub_data.get("execution_details")
                            if exec_details:
                                try:
                                    det = json.loads(exec_details)
                                    st.markdown("#### Test Case Breakdown:")
                                    for tc_res in det.get("details", []):
                                        tc_stat = tc_res.get("status")
                                        if tc_stat == "Passed":
                                            st.write(f"✅ Test Case {tc_res['test_case_number']}: **Passed**")
                                        else:
                                            st.write(f"❌ Test Case {tc_res['test_case_number']}: **{tc_stat}** (Expected: `{tc_res.get('expected_output')}`, Got: `{tc_res.get('actual_output')}`)")
                                except Exception:
                                    pass
                        else:
                            st.error("Submission failed. Ensure backend service is reachable.")

        elif menu == "🏆 Live Leaderboard":
            st.markdown("## 🏆 Class Coding Leaderboard (FR-008)")
            lb = api_get("leaderboard") or []
            if lb:
                df_lb = pd.DataFrame(lb)
                st.dataframe(df_lb[["rank", "student_name", "enrollment_no", "total_score", "problems_solved"]], use_container_width=True)
