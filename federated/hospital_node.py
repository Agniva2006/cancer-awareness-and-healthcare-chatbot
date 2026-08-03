"""
OncoGraph AI — Simulated Multi-Hospital Federated Learning System
Simulates a 3-hospital distributed training environment using FedAvg
without requiring real patient data or network infrastructure.

Hospitals:
  - Hospital Alpha (Memorial Cancer Center) — lung cancer data partition
  - Hospital Beta  (University Health System) — breast cancer data partition
  - Hospital Gamma (General Research Hospital) — colorectal cancer data partition

Algorithm: Federated Averaging (FedAvg) with numpy weight simulation.
"""

import numpy as np
from typing import Dict, Any, List
import time
import json


class HospitalNode:
    """Simulates a single hospital federated learning client."""

    def __init__(self, name: str, hospital_id: str, data_partition: str,
                 n_samples: int, cancer_focus: str):
        self.name = name
        self.hospital_id = hospital_id
        self.data_partition = data_partition
        self.n_samples = n_samples
        self.cancer_focus = cancer_focus

        # Simulate local model weights (3-layer MLP: 128->64->32->1)
        np.random.seed(hash(hospital_id) % 2**31)
        self.weights = {
            "layer_1": np.random.randn(128, 64).astype(np.float32) * 0.01,
            "bias_1": np.zeros(64, dtype=np.float32),
            "layer_2": np.random.randn(64, 32).astype(np.float32) * 0.01,
            "bias_2": np.zeros(32, dtype=np.float32),
            "layer_3": np.random.randn(32, 1).astype(np.float32) * 0.01,
            "bias_3": np.zeros(1, dtype=np.float32),
        }
        self.training_loss_history = []
        self.training_rounds = 0

    def local_train(self, global_weights: Dict[str, np.ndarray] = None,
                    epochs: int = 5, lr: float = 0.001) -> Dict[str, Any]:
        """
        Simulate local training on hospital's private data partition.
        Returns updated weights and training metrics.
        """
        if global_weights:
            # Download global model
            for key in self.weights:
                self.weights[key] = global_weights[key].copy()

        # Simulate local SGD training
        initial_loss = float(np.random.uniform(0.6, 1.2))
        losses = [initial_loss]
        for epoch in range(epochs):
            # Simulate gradient descent
            for key in self.weights:
                gradient = np.random.randn(*self.weights[key].shape).astype(np.float32) * 0.001
                self.weights[key] -= lr * gradient
            loss = losses[-1] * np.random.uniform(0.85, 0.95)
            losses.append(round(float(loss), 4))

        self.training_loss_history.extend(losses)
        self.training_rounds += 1

        return {
            "hospital_id": self.hospital_id,
            "hospital_name": self.name,
            "cancer_focus": self.cancer_focus,
            "n_samples": self.n_samples,
            "rounds_completed": self.training_rounds,
            "local_epochs": epochs,
            "loss_start": losses[0],
            "loss_end": losses[-1],
            "loss_improvement": round((losses[0] - losses[-1]) / losses[0] * 100, 2),
        }


class FederatedServer:
    """
    Central aggregation server implementing FedAvg.
    Coordinates training across all hospital nodes and
    aggregates weights proportionally to data volume.
    """

    def __init__(self):
        self.hospitals: List[HospitalNode] = [
            HospitalNode(
                name="Memorial Cancer Center",
                hospital_id="HOSP_ALPHA",
                data_partition="lung_cancer",
                n_samples=4200,
                cancer_focus="NSCLC / SCLC"
            ),
            HospitalNode(
                name="University Health System",
                hospital_id="HOSP_BETA",
                data_partition="breast_cancer",
                n_samples=3800,
                cancer_focus="Breast Cancer (HER2+, TNBC, HR+)"
            ),
            HospitalNode(
                name="General Research Hospital",
                hospital_id="HOSP_GAMMA",
                data_partition="colorectal_cancer",
                n_samples=2900,
                cancer_focus="Colorectal / Pancreatic Adenocarcinoma"
            ),
        ]
        self.global_weights = None
        self.round_history = []
        self.current_round = 0

    def _fedavg_aggregate(self, hospital_weights: List[Dict[str, np.ndarray]],
                          sample_counts: List[int]) -> Dict[str, np.ndarray]:
        """Federated Averaging: weighted mean of model parameters."""
        total_samples = sum(sample_counts)
        aggregated = {}
        for key in hospital_weights[0]:
            weighted_sum = np.zeros_like(hospital_weights[0][key])
            for i, weights in enumerate(hospital_weights):
                weighted_sum += weights[key] * (sample_counts[i] / total_samples)
            aggregated[key] = weighted_sum
        return aggregated

    def run_round(self, local_epochs: int = 5) -> Dict[str, Any]:
        """Execute one complete federated training round."""
        self.current_round += 1
        round_start = time.time()

        # Step 1: Distribute global weights to all hospitals
        hospital_results = []
        all_weights = []
        sample_counts = []

        for hospital in self.hospitals:
            result = hospital.local_train(
                global_weights=self.global_weights,
                epochs=local_epochs
            )
            hospital_results.append(result)
            all_weights.append(hospital.weights.copy())
            sample_counts.append(hospital.n_samples)

        # Step 2: FedAvg aggregation
        self.global_weights = self._fedavg_aggregate(all_weights, sample_counts)

        round_time = round(time.time() - round_start, 3)

        round_report = {
            "round": self.current_round,
            "participating_hospitals": len(self.hospitals),
            "total_samples": sum(sample_counts),
            "round_time_seconds": round_time,
            "hospital_reports": hospital_results,
            "global_model_updated": True,
            "aggregation_method": "FedAvg (Weighted by sample count)",
        }

        self.round_history.append(round_report)
        return round_report

    def run_full_training(self, n_rounds: int = 5, local_epochs: int = 5) -> Dict[str, Any]:
        """Execute a full federated training session across multiple rounds."""
        all_round_reports = []
        training_start = time.time()

        for r in range(n_rounds):
            report = self.run_round(local_epochs=local_epochs)
            all_round_reports.append(report)

        total_time = round(time.time() - training_start, 3)

        return {
            "total_rounds": n_rounds,
            "local_epochs_per_round": local_epochs,
            "total_training_time_seconds": total_time,
            "hospitals": [
                {
                    "id": h.hospital_id,
                    "name": h.name,
                    "focus": h.cancer_focus,
                    "samples": h.n_samples,
                    "rounds_completed": h.training_rounds,
                    "final_loss": round(h.training_loss_history[-1], 4) if h.training_loss_history else None,
                    "loss_history": [round(l, 4) for l in h.training_loss_history],
                }
                for h in self.hospitals
            ],
            "rounds": all_round_reports,
            "status": "TRAINING_COMPLETE",
            "privacy_guarantee": "No raw patient data was exchanged between hospital nodes. Only model weight gradients were aggregated.",
        }

    def get_status(self) -> Dict[str, Any]:
        """Return current federated system status."""
        return {
            "total_hospitals": len(self.hospitals),
            "current_round": self.current_round,
            "global_model_initialized": self.global_weights is not None,
            "hospitals": [
                {
                    "id": h.hospital_id,
                    "name": h.name,
                    "focus": h.cancer_focus,
                    "samples": h.n_samples,
                    "rounds_completed": h.training_rounds,
                    "latest_loss": round(h.training_loss_history[-1], 4) if h.training_loss_history else None,
                }
                for h in self.hospitals
            ],
            "privacy_guarantee": "Federated Averaging (FedAvg) — no PHI leaves hospital nodes.",
        }


# Singleton server instance
federated_server = FederatedServer()
