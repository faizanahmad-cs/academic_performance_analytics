import unittest
from backend.app.database import SessionLocal
from backend.app.models import User, Student, Course, AcademicRecord, Attendance, Assignment, Submission, RiskPrediction
from backend.app.ml_engine import risk_engine
from backend.app.judge0_service import judge_service
from backend.app.main import get_hod_dashboard, get_student_dashboard, get_leaderboard

class TestAcademicAnalyticsCore(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_01_user_and_student_count(self):
        student_count = self.db.query(Student).count()
        self.assertEqual(student_count, 60, f"Expected 60 students, found {student_count}")
        
        hod = self.db.query(User).filter(User.email == "hod@amu.ac.in").first()
        self.assertIsNotNone(hod)
        self.assertEqual(hod.role, "HOD")

    def test_02_course_count(self):
        course_count = self.db.query(Course).count()
        self.assertEqual(course_count, 12, f"Expected 12 courses, found {course_count}")

    def test_03_hod_dashboard_metrics(self):
        data = get_hod_dashboard(self.db)
        self.assertEqual(data.total_students, 60)
        self.assertGreater(data.average_marks, 50.0)
        self.assertGreater(data.overall_attendance, 50.0)
        self.assertGreaterEqual(data.high_risk_count, 0)
        self.assertEqual(len(data.subject_averages), 12)

    def test_04_student_dashboard(self):
        # Student 1 is Faizan Ahmad (GR0622)
        data = get_student_dashboard(1, self.db)
        self.assertEqual(data.student_info.enrollment_no, "GR0622")
        self.assertEqual(len(data.sem1_marks), 6)
        self.assertEqual(len(data.sem2_marks), 6)
        self.assertIsNotNone(data.risk_prediction)
        self.assertIn(data.risk_prediction.risk_level, ["Low", "Medium", "High"])

    def test_05_ml_risk_engine(self):
        # Test low risk sample
        low_risk_features = {
            "sem1_avg": 85.0,
            "sem2_avg": 88.0,
            "overall_avg": 86.5,
            "sem1_attendance": 92.0,
            "sem2_attendance": 90.0,
            "overall_attendance": 91.0,
            "trend": 3.0,
            "min_mark": 75.0,
            "failed_count": 0
        }
        pred_low = risk_engine.predict(low_risk_features)
        self.assertEqual(pred_low["risk_level"], "Low")

        # Test high risk sample (attendance < 70% or multiple fails)
        high_risk_features = {
            "sem1_avg": 42.0,
            "sem2_avg": 38.0,
            "overall_avg": 40.0,
            "sem1_attendance": 62.0,
            "sem2_attendance": 65.0,
            "overall_attendance": 63.5,
            "trend": -4.0,
            "min_mark": 28.0,
            "failed_count": 3
        }
        pred_high = risk_engine.predict(high_risk_features)
        self.assertEqual(pred_high["risk_level"], "High")
        self.assertTrue(len(pred_high["recommendations"]) > 0)

    def test_06_code_evaluation(self):
        code = "nums = list(map(int, input().split()))\nprint(sum(nums))"
        test_cases = [
            {"input": "1 2 3 4 5", "expected_output": "15"},
            {"input": "10 20", "expected_output": "30"}
        ]
        result = judge_service.evaluate_submission(code, "python", test_cases)
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(result["status"], "Accepted")
        self.assertEqual(result["passed_test_cases"], 2)

    def test_07_leaderboard(self):
        lb = get_leaderboard(self.db)
        self.assertGreater(len(lb), 0)
        self.assertEqual(lb[0].rank, 1)

if __name__ == "__main__":
    unittest.main()
