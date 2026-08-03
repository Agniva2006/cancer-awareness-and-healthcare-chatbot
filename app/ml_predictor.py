"""
OncoGraph AI — Machine Learning Prognosis Predictor
Trains a local Scikit-Learn Random Forest model on synthetic oncology data
to predict malignancy risk (Low, Moderate, High) from clinical features.
"""

import numpy as np
import pickle
from pathlib import Path
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


class OncologyMLPredictor:
    """
    Local ML system to predict cancer malignancy risk level.
    Features: [Age, TumorSize_cm, LymphNodes, Biomarker_Encoded, SymptomCount]
    Classes: 0 (Low Risk / Benign), 1 (Moderate Risk / Localized), 2 (High Risk / Metastatic)
    """

    def __init__(self):
        self.model_dir = Path(__file__).resolve().parent.parent / "data"
        self.model_dir.mkdir(exist_ok=True)
        self.model_path = self.model_dir / "prognosis_model.pkl"
        self.scaler_path = self.model_dir / "prognosis_scaler.pkl"
        self.model = None
        self.scaler = None

        # Auto-train on startup if model doesn't exist
        self._load_or_train()

    def _generate_synthetic_data(self, n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """Generate high-quality synthetic clinical dataset for training."""
        np.random.seed(42)

        # Features: Age (20-85), Tumor Size (0.5 - 10.0 cm), Lymph Nodes (0 or 1), Biomarker (0-4), Symptoms (0-5)
        age = np.random.randint(20, 85, n_samples)
        tumor_size = np.random.uniform(0.5, 10.0, n_samples)
        lymph_nodes = np.random.binomial(1, 0.4, n_samples)
        biomarkers = np.random.randint(0, 5, n_samples)  # 0: None, 1: EGFR, 2: HER2, 3: ALK, 4: MSI-H
        symptoms = np.random.randint(0, 6, n_samples)

        X = np.stack([age, tumor_size, lymph_nodes, biomarkers, symptoms], axis=1)

        # Risk scoring heuristic to assign labels
        # Score = (TumorSize * 1.5) + (LymphNodes * 3) + (Age > 60 * 1.0) + (Biomarkers > 0 * 1.2) + (Symptoms * 0.8)
        scores = (tumor_size * 1.5) + (lymph_nodes * 3.0) + ((age > 60).astype(int) * 1.0) + ((biomarkers > 0).astype(int) * 1.2) + (symptoms * 0.8)

        # Standardize labels: Low (Score < 6), Moderate (6 <= Score < 12), High (Score >= 12)
        y = np.zeros(n_samples, dtype=int)
        y[scores >= 6.0] = 1
        y[scores >= 12.0] = 2

        return X, y

    def _load_or_train(self):
        """Load saved Random Forest model, or train a new one if not found."""
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(self.scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
            else:
                self.train_model()
        except Exception:
            # Fallback to training
            self.train_model()

    def train_model(self):
        """Train Random Forest classifier on synthetic dataset and save assets."""
        X, y = self._generate_synthetic_data(1200)

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        self.model.fit(X_scaled, y)

        # Save to disk
        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)
        with open(self.scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)

    def predict_risk(self, age: int, tumor_size: float, lymph_nodes: int,
                     biomarker_id: str, symptom_count: int) -> Dict[str, Any]:
        """
        Predict malignancy risk score and category probability.
        Biomarker encoding: None=0, EGFR=1, HER2=2, ALK=3, MSI=4
        """
        if self.model is None or self.scaler is None:
            self._load_or_train()

        # Encode biomarker
        biomarker_map = {"NONE": 0, "EGFR_EX19DEL": 1, "EGFR_L858R": 1, "EGFR_T790M": 1,
                         "HER2_AMP": 2, "ALK_FUSION": 3, "MSI_H": 4}
        biomarker_val = biomarker_map.get(biomarker_id.upper(), 0)

        # Format input feature vector
        features = np.array([[age, tumor_size, lymph_nodes, biomarker_val, symptom_count]], dtype=np.float32)
        features_scaled = self.scaler.transform(features)

        # Run predictions
        pred_class = int(self.model.predict(features_scaled)[0])
        probabilities = self.model.predict_proba(features_scaled)[0]

        risk_classes = ["LOW_RISK (Benign/Localized)", "MODERATE_RISK (Localized/Regional)", "HIGH_RISK (Advanced/Metastatic)"]
        colors = ["green", "yellow", "red"]

        # Feature importances
        importances = self.model.feature_importances_
        feature_names = ["Age", "Tumor Size", "Lymph Node Involvement", "Biomarker profile", "Symptom count"]
        importance_chart = {feature_names[i]: round(float(importances[i]) * 100, 2) for i in range(len(importances))}

        return {
            "prediction_class": pred_class,
            "prediction_label": risk_classes[pred_class],
            "color_theme": colors[pred_class],
            "probabilities": {
                "low": round(float(probabilities[0]) * 100, 2),
                "moderate": round(float(probabilities[1]) * 100, 2),
                "high": round(float(probabilities[2]) * 100, 2),
            },
            "feature_importance": importance_chart,
            "clinical_notes": self._generate_clinical_notes(pred_class, tumor_size, lymph_nodes)
        }

    def _generate_clinical_notes(self, risk_class: int, tumor_size: float, lymph_nodes: int) -> str:
        if risk_class == 0:
            return "Indicates localized presentation. Standard clinical monitoring is recommended. Surgical resection may be curative."
        elif risk_class == 1:
            return f"Moderate risk detected with tumor size of {tumor_size}cm. Check for regional lymph nodes. Recommend chemotherapy staging and possible radiotherapy planning."
        else:
            status = "with lymph node involvement" if lymph_nodes else "large tumor bulk"
            return f"High risk metastatic profile predicted {status}. Initiate systemic therapy immediately. Coordinate multi-disciplinary tumor board consult."


# Singleton ML Predictor instance
ml_predictor = OncologyMLPredictor()
