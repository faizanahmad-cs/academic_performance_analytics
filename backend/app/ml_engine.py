import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), "risk_model.joblib")

class AcademicRiskEngine:
    def __init__(self):
        self.pipeline = None
        self.feature_names = [
            "sem1_avg",
            "sem2_avg",
            "overall_avg",
            "sem1_attendance",
            "sem2_attendance",
            "overall_attendance",
            "trend",
            "min_mark",
            "failed_count"
        ]
        self._load_or_train()

    def _determine_ground_truth_label(self, row: Dict[str, float]) -> str:
        """
        Rule-based heuristic used for generating ground truth supervision
        adhering to academic standards (AMU grading/attendance criteria).
        """
        overall_avg = row["overall_avg"]
        overall_att = row["overall_attendance"]
        min_mark = row["min_mark"]
        failed_count = row["failed_count"]
        trend = row["trend"]

        # High Risk criteria: Low attendance (<70%) OR average < 50 OR multiple backlogs/fails OR severe drop
        if overall_att < 70.0 or overall_avg < 50.0 or failed_count >= 2 or (min_mark < 35.0 and trend < -15.0):
            return "High"
        # Medium Risk criteria: Moderate attendance (70-75%) OR average 50-65% OR 1 failed subject
        elif overall_att < 75.0 or overall_avg < 65.0 or failed_count == 1:
            return "Medium"
        # Low Risk: Safe attendance (>=75%), average >= 65%, no failed subjects
        else:
            return "Low"

    def _generate_synthetic_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate diverse academic training samples covering various mark distributions,
        attendance values, and performance trends.
        """
        np.random.seed(42)
        n_samples = 1200
        
        sem1_avg = np.random.uniform(35, 95, n_samples)
        trend = np.random.normal(0, 10, n_samples)
        sem2_avg = np.clip(sem1_avg + trend, 30, 98)
        overall_avg = (sem1_avg + sem2_avg) / 2.0
        
        sem1_att = np.random.uniform(55, 98, n_samples)
        sem2_att = np.random.uniform(55, 98, n_samples)
        overall_att = (sem1_att + sem2_att) / 2.0
        
        min_mark = np.clip(sem1_avg - np.random.uniform(5, 25, n_samples), 20, 95)
        failed_count = np.random.choice([0, 1, 2, 3], size=n_samples, p=[0.70, 0.18, 0.08, 0.04])

        X = []
        y = []
        for i in range(n_samples):
            features = {
                "sem1_avg": sem1_avg[i],
                "sem2_avg": sem2_avg[i],
                "overall_avg": overall_avg[i],
                "sem1_attendance": sem1_att[i],
                "sem2_attendance": sem2_att[i],
                "overall_attendance": overall_att[i],
                "trend": trend[i],
                "min_mark": min_mark[i],
                "failed_count": failed_count[i]
            }
            label = self._determine_ground_truth_label(features)
            row_vector = [features[k] for k in self.feature_names]
            X.append(row_vector)
            y.append(label)

        return np.array(X), np.array(y)

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.pipeline = joblib.load(MODEL_PATH)
                return
            except Exception:
                pass
        
        # Train new model
        X, y = self._generate_synthetic_training_data()
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42))
        ])
        self.pipeline.fit(X, y)
        try:
            joblib.dump(self.pipeline, MODEL_PATH)
        except Exception:
            pass

    def predict(self, feature_dict: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict risk category and provide actionable recommendations.
        """
        row_vector = [feature_dict.get(k, 0.0) for k in self.feature_names]
        X = np.array([row_vector])
        
        pred_label = self.pipeline.predict(X)[0]
        classes = list(self.pipeline.classes_)
        probabilities = self.pipeline.predict_proba(X)[0]
        prob_dict = {cls: round(float(prob), 3) for cls, prob in zip(classes, probabilities)}

        # Risk recommendations
        recommendations = []
        if pred_label == "High":
            recommendations.append("Immediate academic counseling and parental notification recommended.")
            if feature_dict.get("overall_attendance", 100) < 75.0:
                recommendations.append(f"Attendance ({feature_dict.get('overall_attendance', 0):.1f}%) is below mandatory 75% AMU requirement.")
            if feature_dict.get("failed_count", 0) > 0:
                recommendations.append(f"Remedial classes needed for {int(feature_dict.get('failed_count', 0))} subject(s) with marks below pass criteria.")
            if feature_dict.get("trend", 0) < -10.0:
                recommendations.append(f"Significant grade decline of {abs(feature_dict.get('trend', 0)):.1f}% from Semester 1 to Semester 2.")
        elif pred_label == "Medium":
            recommendations.append("Regular monitoring recommended during practical and tutorial classes.")
            if feature_dict.get("overall_attendance", 100) < 75.0:
                recommendations.append("Attendance requires improvement to satisfy university examination eligibility.")
            if feature_dict.get("trend", 0) < 0:
                recommendations.append("Marginal drop in Semester 2 performance; needs extra practice in programming and theory.")
            else:
                recommendations.append("Performance is moderate; target > 70% in upcoming internal assessments.")
        else:
            recommendations.append("Satisfactory academic progress. Eligible for advanced assignments and peer mentoring.")
            if feature_dict.get("overall_attendance", 0) >= 85.0:
                recommendations.append("Excellent attendance record.")

        return {
            "risk_level": pred_label,
            "probabilities": prob_dict,
            "recommendations": recommendations,
            "features": {k: round(float(v), 2) for k, v in feature_dict.items()}
        }

risk_engine = AcademicRiskEngine()
